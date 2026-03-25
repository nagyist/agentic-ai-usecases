"""LangGraph-based booking agent with state-driven conversation flow."""

import os
from typing import TypedDict, Annotated, List, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from services.doctor_service import get_specialities_list, get_doctor_info, generate_time_slots
# from services.booking_service import get_available_slots, confirm_booking
from services.booking_service import confirm_booking

# Initialize OpenAI client
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class BookingState(TypedDict):
    """State for the booking conversation."""
    messages: List[dict]
    stage: str  # greeting, select_speciality, select_doctor, select_slot, confirm, completed
    selected_speciality: Optional[str]
    selected_doctor: Optional[dict]
    selected_date: Optional[str]
    selected_slot: Optional[str]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    booking_id: Optional[str]
    available_options: List[str]  # For clickable UI options
    last_interrupt_message: Optional[str] # To track the last interrupt prompt


def create_initial_state():
    """Create initial state for the conversation."""
    return {
        "messages": [],
        "stage": "greeting",
        "selected_speciality": None,
        "selected_doctor": None,
        "selected_date": None,
        "selected_slot": None,
        "customer_name": None,
        "customer_phone": None,
        "booking_id": None,
        "available_options": []
    }


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
    max_tokens: int = 50,
) -> str:
    """
    Centralized helper for all LLM calls.
    Returns the assistant's response
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        print(f"LLM response: {response.choices[0].message.content.strip()}")
        return response
    except Exception as e:
        print(f"LLM call error: {e}")
        return ""

def is_message_on_topic(
    conversation_snippet: List[dict],
    current_stage: str,
    k: int = 4
) -> bool:
    """
    Guardrail: Uses LLM-only semantic classification to determine whether
    the recent conversation is related to booking a medical appointment.

    Args:
        messages: Full conversation history
        current_stage: Current booking stage
        k: Number of recent messages to include for context

    Returns:
        True if related to booking, False otherwise.
    """

    if not conversation_snippet:
        return True  # Nothing to evaluate

    # Map stage to human-readable context
    stage_context = {
        "greeting": "booking a medical appointment",
        "select_speciality": "choosing a medical speciality",
        "select_doctor": "choosing a doctor",
        "select_date": "choosing a date for appointment",
        "select_slot": "choosing an appointment time",
        "confirm": "confirming an appointment",
        "collect_details": "getting the customer details for the appointment",
    }

    context = stage_context.get(current_stage, "booking a medical appointment")

    # Get last k messages for context
    # recent_messages = messages[-k:]

    # conversation_snippet = "\n".join(
    #     f"{m['role'].upper()}: {m['content']}"
    #     for m in recent_messages
    # )

    try:
        response = call_llm(
            system_prompt="""You are an intent classifier for a medical clinic booking system.

            Determine whether the conversation is related to booking a medical appointment, selecting a specialty/doctor, or discussing health concerns.

            Respond with ONLY:
            - 'yes' → if the user is discussing medical topics, symptoms, doctors, or appointment details.
            - 'no' → if the user is discussing completely unrelated topics like politics, sports, entertainment, finance, or general knowledge.

            Do not explain. Only return 'yes' or 'no'.""",
                        user_prompt=f"""
            Current stage context: {context}

            Recent conversation:
            {conversation_snippet}

            Is this conversation on-topic for booking a medical appointment at a clinic?
            """,
            max_tokens=5
        )

        result = response.choices[0].message.content.strip().lower()

        return result == "yes"

    except Exception as e:
        print(f"⚠️ Topic check error: {e}. Allowing message through.")
        return True 


# Define valid routes for each stage (used to prevent invalid routing)
VALID_ROUTES_PER_STAGE = {
    "greeting": {"greeting", "select_speciality", "cancelled"},
    "select_speciality": {"select_speciality", "select_doctor"},
    "select_doctor": {"select_date"},  # This node always goes to select_date
    "select_date": {"select_date", "select_slot"},
    "select_slot": {"select_slot", "confirm"},
    "confirm": {"confirm", "collect_details", "cancelled", "select_slot"},
    "collect_details": {"collect_details", "completed"}
}


def llm_router(state: BookingState, k=4) -> str:
    """
    Routes the conversation based on user intent while enforcing guardrails.
    
    Logic:
    1. Check if message is on-topic; if not, add guardrail response and stay in current stage
    2. Route based on stage-specific logic
    3. Validate route is allowed for current stage; if not, default to current stage
    """
    current_stage = state.get("stage", "greeting")
    messages = state.get("messages", [])
    recent_messages = messages[-k:]
    conversation_snippet = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in recent_messages)
    
    # ===== STATE-BASED BYPASS: Route based on state logic before calling LLM =====
    # If a specialty is already selected, move to doctor selection automatically
    if current_stage == "select_speciality" and state.get("selected_speciality"):
        print(f"State-based bypass: specialty '{state['selected_speciality']}' selected. Moving to select_doctor.")
        return "select_doctor"
    
    # If a date and slot are already selected, move to confirmation
    if current_stage == "select_date" and state.get("selected_date"):
        return "select_slot"
    
    if current_stage == "select_slot" and state.get("selected_slot"):
        return "confirm"
            
    # ===== GUARDRAIL: Off-Topic Detection =====
    if state["messages"] and not is_message_on_topic(conversation_snippet, current_stage, k=k):
        try:
            response = call_llm(
                system_prompt="""You are a friendly clinic booking assistant.
                When users ask off-topic questions, politely decline and redirect to booking.
                Keep response to 1-2 sentences. Be warm and helpful.""",
                user_prompt=f"""User asked something off-topic: "{conversation_snippet}"
                Generate a redirect response that politely declines and asks if they want to continue booking.""",
                max_tokens=50
            )
            off_topic_response = response.choices[0].message.content.strip()
            print(f"Generated off-topic response: {off_topic_response}")
        except:
            off_topic_response = "I'm sorry, I can only help with clinic bookings. Would you like to continue with your appointment?"
        
        state["messages"].append({
            "role": "assistant",
            "content": off_topic_response
        })
        return current_stage  # Stay in current stage

    # ===== ROUTING LOGIC: Route based on current stage and user message =====
    routing_prompts = {
        "greeting": f"""Analyze the conversation:
        {conversation_snippet}
        
        Does the user want to book an appointment or continue with a booking? 
        Respond with ONLY: 
        - 'select_speciality' if they want to book or start the process.
        - 'cancelled' if they explicitly want to stop.
        - 'greeting' if they are just saying hi or being conversational without a clear intent yet.""",

        "select_speciality": f"""Analyze the conversation:
        {conversation_snippet}
        
        Has a medical specialty been successfully identified or chosen from the available list? 
        (Current specialty in state: {state['selected_speciality'] or 'None'})
        
        Respond with ONLY: 'select_doctor' if chosen, 'select_speciality' if not yet clear.""",

        "select_date": f"""Analyze the conversation:
        {conversation_snippet}
        
        Has a date been chosen for the appointment?
        (Current date in state: {state['selected_date'] or 'None'})
        
        Respond with ONLY: 'select_slot' if chosen, 'select_date' if not yet clear.""",

        "select_slot": f"""Analyze the conversation:
        {conversation_snippet}
        
        Has a specific time slot been selected?
        (Current slot in state: {state['selected_slot'] or 'None'})
        
        Respond with ONLY: 'confirm' if selected, 'select_slot' if not yet clear.""",

        "confirm": f"""Analyze the user's response: "{conversation_snippet}"
                    Does the user want to proceed with this appointment? 
                    Respond with ONLY: 
                    - 'collect_details' if they say yes, okay, confirm, or agree.
                    - 'cancelled' if they say no, cancel, or stop.
                    - 'select_slot' if they want to change the time or pick a different slot.
                    - 'confirm' if it is unclear and you need to ask again.
                    """
            }

    # If no routing prompt for this stage, return current stage (node handles transitions)
    if current_stage not in routing_prompts:
        return current_stage

    try:
        response = call_llm(
            system_prompt="You are a conversational AI routing expert. Always respond with ONLY the exact route name.",
            user_prompt=routing_prompts[current_stage],
            max_tokens=20
        )
        route = response.choices[0].message.content.strip().lower().replace("'", "").replace('"', "").strip()
        print(f"Routing decision: {route}")
    except Exception as e:
        print(f"⚠️ Routing error: {e}. Defaulting to {current_stage}")
        return current_stage

    # ===== VALIDATION: Ensure route is valid for current stage =====
    valid_routes = VALID_ROUTES_PER_STAGE.get(current_stage, {current_stage})
    
    if route not in valid_routes:
        print(f"⚠️ Invalid route '{route}' for stage '{current_stage}'. Valid: {valid_routes}. Defaulting to '{current_stage}'")
        return current_stage
    
    return route


def greeting_node(state: BookingState) -> BookingState:
    """Greets the user and pauses to see if they want to book."""
    state["stage"] = "greeting"
    
    # Default message
    msg = "👋 Welcome to CarePlus! Would you like to book an appointment?"
    
    # If there's user input, use LLM to respond friendly
    if state["messages"] and state["messages"][-1]["role"] == "user":
        conversation_snippet = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in state["messages"][-2:]
        )
        try:
            response = call_llm(
                system_prompt="""You are a friendly clinic booking assistant for CarePlus Clinic.
                Respond naturally to the user's greeting and ask if they'd like to book an appointment.
                Keep it to 1 sentence.""",
                user_prompt=f"Recent conversation:\n{conversation_snippet}\nAssistant:",
                max_tokens=50
            )
            llm_msg = response.choices[0].message.content.strip()
            if llm_msg:
                msg = llm_msg
        except:
            pass

    # If this is the first time in this node (no messages yet or last message was user)
    if not state["messages"] or state["messages"][-1]["role"] != "assistant":
        state["messages"].append({
            "role": "assistant", 
            "content": msg,
            "options": ["Book Appointment"]
        })
    
    user_input = interrupt({
        "role": "assistant",
        "content": msg,
        "available_options": ["Book Appointment"]
    })
    state["messages"].append({"role": "user", "content": user_input})
    return state


def select_speciality_node(state: BookingState) -> BookingState:
    """Handle speciality selection."""
    state["stage"] = "select_speciality"
    specialities = get_specialities_list()
    msg = "Please choose a speciality:"

    # Only append the prompt if it's not already the last message
    # or if the last message wasn't an "unknown" error message which already serves as a prompt
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    if last_msg != msg and "didn't recognize" not in last_msg.lower():
        state["messages"].append({
            "role": "assistant",
            "content": msg,
            "options": specialities
        })

    raw_user_input = interrupt({
        "role": "assistant",
        "content": msg,
        "available_options": specialities
    })
    
    prompt = f"""Extract the medical speciality from: "{raw_user_input}"
    Available specialities: {', '.join(specialities)}
    Return ONLY the exact name from the list or "UNKNOWN"."""
    
    try:
        response = call_llm(
            system_prompt="You extract information from messages.",
            user_prompt=prompt,
            max_tokens=30
        )
        extracted = response.choices[0].message.content.strip()

        selected = None
        for spec in specialities:
            if spec.lower() in extracted.lower() or extracted.lower() in spec.lower():
                selected = spec
                break
        
        if selected:
            state["selected_speciality"] = selected
            state["messages"].append({"role": "user", "content": raw_user_input})
        else:
            state["messages"].append({
                "role": "assistant", 
                "content": f"I didn't recognize that. Pick from: {', '.join(specialities)}"
            })
    except Exception as e:
        print(f"Extraction error: {e}")

    return state


def select_doctor_node(state: BookingState) -> BookingState:
    """Identify the doctor and move to slot selection."""
    speciality = state["selected_speciality"]
    doctor = get_doctor_info(speciality)
    
    if not doctor:
        state["messages"].append({
            "role": "assistant",
            "content": "Sorry, no doctor available. Try another speciality."
        })
        state["stage"] = "select_speciality"
        return state
    
    state["selected_doctor"] = doctor
    state["stage"] = "select_date"
    return state

def select_date_node(state: BookingState) -> BookingState:
    """Handle date selection using interrupt and LLM extraction."""
    state["stage"] = "select_date"
    doctor = state["selected_doctor"]

    
    
    # Simple date options for demo
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now().replace(day=datetime.now().day + 1)).strftime("%Y-%m-%d")
    available_dates = ["Today", "Tomorrow"]

    title = f"We have {state['selected_speciality']}, {doctor['doctor_name']}. When would you like to visit? We have slots for Today ({today}) and Tomorrow ({tomorrow})."
    if not state["messages"] or state["messages"][-1]["content"] != title:
        state["messages"].append({
            "role": "assistant",
            "content": title,
            "options": available_dates
        })
    raw_user_input = interrupt({
        "role": "assistant",
        "content": title,
        "available_options": available_dates
    })

    prompt = f"""Extract the date from: "{raw_user_input}"
    Relative references: Today is {today}, Tomorrow is {tomorrow}.
    Respond with ONLY the date in YYYY-MM-DD format or "UNKNOWN"."""

    try:
        response = call_llm(
            system_prompt="You extract dates from messages.",
            user_prompt=prompt,
            max_tokens=20
        )
        extracted = response.choices[0].message.content.strip()

        # Simple mapping for common inputs if LLM output is slightly off
        if "today" in raw_user_input.lower():
            selected = today
        elif "tomorrow" in raw_user_input.lower():
            selected = tomorrow
        else:
            selected = extracted if extracted != "UNKNOWN" else None

        if selected:
            state["selected_date"] = selected
            state["messages"].append({"role": "user", "content": raw_user_input})
        else:
            state["messages"].append({
                "role": "assistant",
                "content": "I'm sorry, I couldn't understand the date. Could you please specify if you want Today or Tomorrow?"
            })
    except Exception as e:
        print(f"Date extraction error: {e}")

    return state


def select_slot_node(state: BookingState) -> BookingState:
    """Handle time slot selection using interrupt and LLM extraction."""
    state["stage"] = "select_slot"
    doctor = state["selected_doctor"]
    available_slots = generate_time_slots(doctor["office_timing"])

    message = f"Pick a slot: {', '.join(available_slots)}"

    if state["messages"][-1]["content"] != message:
        state["messages"].append({
            "role": "assistant",
            "content": message,
            "options": available_slots
        })

    raw_user_input = interrupt({
        "role": "assistant",
        "content": message,
        "available_options": available_slots
    })

    prompt = f"""Extract the time slot from: "{raw_user_input}"
    Available: {', '.join(available_slots)}
    Respond with ONLY the exact time slot or "UNKNOWN"."""

    try:
        response = call_llm(
            system_prompt="You extract time slots from messages.",
            user_prompt=prompt,
            max_tokens=20
        )
        extracted = response.choices[0].message.content.strip()

        selected = next((s for s in available_slots if s.lower() in extracted.lower()), None)

        if selected:
            state["selected_slot"] = selected
            state["messages"].append({"role": "user", "content": raw_user_input})
        else:
            state["messages"].append({
                "role": "assistant",
                "content": "I didn't catch that. Which slot works?"
            })
    except Exception as e:
        print(f"Slot extraction error: {e}")

    return state


def confirm_node(state: BookingState) -> BookingState:
    """Handle confirmation stage."""
    state["stage"] = "confirm"
    doctor = state["selected_doctor"]
    slot = state["selected_slot"]
    date = state["selected_date"] or "Today"
    
    message = f"""Review your appointment:

**Doctor:** {doctor['doctor_name']}
**Speciality:** {doctor['speciality']}
**Date:** {date}
**Time:** {slot}

Confirm or Cancel?"""
    
    options = ["Confirm", "Cancel", "Change Slot"]

    # Ensure the confirmation message is in history before interrupting
    if not state["messages"] or state["messages"][-1].get("content") != message:
        state["messages"].append({
            "role": "assistant", 
            "content": message,
            "options": options
        })

    user_choice = interrupt({
        "role": "assistant",
        "content": message,
        "available_options": options
    })

    state["messages"].append({
        "role": "user",
        "content": user_choice
    })
    
    return state


def collect_details_node(state: BookingState) -> BookingState:
    """Collect patient details before final booking."""
    
    msg_name = "Please enter your full name:"
    if state["messages"][-1]["content"] != msg_name:
        state["messages"].append({"role": "assistant", "content": msg_name})
    name = interrupt(msg_name)
    state["messages"].append({"role": "user", "content": name})

    msg_phone = "Please enter your phone number:"
    if state["messages"][-1]["content"] != msg_phone:
        state["messages"].append({"role": "assistant", "content": msg_phone})
    phone = interrupt(msg_phone)
    state["messages"].append({"role": "user", "content": phone})

    state["customer_name"] = name
    state["customer_phone"] = phone
    state["stage"] = "completed"

    return state


def completed_node(state: BookingState) -> BookingState:
    """Finalize booking and insert into database."""
    state["stage"] = "completed"
    doctor = state["selected_doctor"]
    slot = state["selected_slot"]
    date = state["selected_date"]
    name = state["customer_name"]
    phone = state["customer_phone"]

    # 🔥 REAL DATABASE INSERT
    booking_id = confirm_booking(
        doctor_id=doctor["doctor_id"],
        customer_name=name,
        customer_phone=phone,
        time_slot=slot,
        appointment_date=date
    )

    state["booking_id"] = booking_id

    message = f"""✅ Appointment Confirmed!

                **Booking ID:** {booking_id}
                **Doctor:** {doctor['doctor_name']}
                **Date:** {date}
                **Time:** {slot}

                Thank you for choosing CarePlus Clinic."""
    
    state["messages"].append({
        "role": "assistant",
        "content": message
    })

    state["available_options"] = []
    state["stage"] = "completed"

    return state


def cancelled_node(state: BookingState) -> BookingState:
    """Handle cancelled booking."""
    state["messages"].append({
        "role": "assistant",
        "content": "Thank you for connecting. Send 'hi' to restart your booking.",
        "options": ["Book Again"]
    })

    state["available_options"] = ["Book Again"]
    state["stage"] = "cancelled"

    return state


def build_booking_graph():
    workflow = StateGraph(BookingState)

    # 1. Add Nodes
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("select_speciality", select_speciality_node)
    workflow.add_node("select_doctor", select_doctor_node)
    workflow.add_node("select_date", select_date_node)
    workflow.add_node("select_slot", select_slot_node)
    workflow.add_node("confirm", confirm_node)
    workflow.add_node("collect_details", collect_details_node)
    workflow.add_node("completed", completed_node)
    workflow.add_node("cancelled", cancelled_node)

    # 2. Set Entry Point
    workflow.set_entry_point("greeting")

    # 3. Add Conditional Edges WITH MAPPING
    # Format: add_conditional_edges(source_node, routing_function, mapping_dict)
    
    # The greeting node routes based on user intent
    workflow.add_conditional_edges(
        "greeting",
        llm_router,
        {
            "greeting": "greeting",
            "select_speciality": "select_speciality",
            "cancelled": "cancelled"
        }
    )

    workflow.add_conditional_edges(
        "select_speciality",
        llm_router,
        {
            "select_speciality": "select_speciality",
            "select_doctor": "select_doctor"
        }
    )

    # Transition from doctor to date
    workflow.add_edge("select_doctor", "select_date")

    workflow.add_conditional_edges(
        "select_date",
        llm_router,
        {
            "select_date": "select_date",
            "select_slot": "select_slot"
        }
    )

    workflow.add_conditional_edges(
        "select_slot",
        llm_router,
        {
            "select_slot": "select_slot",
            "confirm": "confirm"
        }
    )

    workflow.add_conditional_edges(
        "confirm",
        llm_router,
        {
            "confirm": "confirm",
            "collect_details": "collect_details",
            "cancelled": "cancelled",
            "select_slot": "select_slot"
        }
    )
    
    workflow.add_edge("collect_details", "completed")
    
    # 4. Final Edges to END
    workflow.add_edge("completed", END)
    workflow.add_edge("cancelled", END)

    # 5. Compile with Checkpointer
    return workflow.compile(checkpointer=MemorySaver())
# Create the compiled graph
booking_graph = build_booking_graph()



def process_message(state: BookingState, user_message: str, thread_id: str = "default_session") -> BookingState:
    """Process a user message through the booking graph."""
    config = {"configurable": {"thread_id": thread_id}}
    
    # Check if the graph is currently interrupted
    current_state = booking_graph.get_state(config)
    
    if current_state.tasks and current_state.tasks[0].interrupts:
        # Resume the graph with the user's message
        result = booking_graph.invoke(Command(resume=user_message), config=config)
    else:
        # No interrupt, so start/continue normally
        # Add user message to state (unless it's an initial trigger)
        if user_message.lower() != "hi" or state["messages"]:
            # Avoid duplicate user messages if already added
            if not state["messages"] or state["messages"][-1].get("content") != user_message:
                state["messages"].append({
                    "role": "user",
                    "content": user_message
                })
        # Run the graph
        result = booking_graph.invoke(state, config=config)
    
    # Update available_options and ensure message is in history
    snapshot = booking_graph.get_state(config)
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        
        # Handle both dict and string interrupt values
        msg_content = ""
        options = []
        if isinstance(interrupt_value, dict):
            msg_content = interrupt_value.get("content", "")
            options = interrupt_value.get("available_options", [])
        else:
            msg_content = str(interrupt_value)
            
        # Ensure the interrupt message is in the chat history
        if msg_content:
            # Check if it was already added by the node
            last_msg_content = result["messages"][-1].get("content", "") if result["messages"] else ""
            if last_msg_content != msg_content:
                result["messages"].append({
                    "role": "assistant",
                    "content": msg_content,
                    "options": options
                })
            else:
                # If already added, just update it with options if missing
                result["messages"][-1]["options"] = options
            
        result["available_options"] = options
    else:
        # If not interrupted, use whatever set in state, or default to empty
        if "available_options" not in result:
            result["available_options"] = []
    
    return result