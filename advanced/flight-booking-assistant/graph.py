import json
import os
import traceback
from typing import TypedDict, List, Dict, Literal
from datetime import datetime
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from openai import OpenAI
from prompts import *
from database import IndigoDB

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client directly
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in environment or .env file")
client = OpenAI(api_key=api_key)

class BookingState(TypedDict):
    messages: List[Dict[str, str]]  # conversation history
    current_agent: str
    next_step: str
    booking_data: Dict
    search_results: List[Dict]
    selected_flight: Dict
    confirmation_step: str  # track sub-steps in confirmation phase

# Helper functions
def llm_call(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """Direct OpenAI API call without LangChain"""
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        if json_mode:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"},
                timeout=30
            )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                timeout=30
            )
        
        return response.choices[0].message.content
    except Exception as e:
        error_msg = f"LLM Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Print to server logs
        raise

def extract_entities(user_message: str, current_state: Dict) -> Dict:
    """Extract structured data using LLM"""
    prompt = f"User message: {user_message}\nCurrent state: {json.dumps(current_state)}"
    result = llm_call(EXTRACTION_SYSTEM_PROMPT, prompt, json_mode=True)
    try:
        return json.loads(result)
    except:
        return {}

def format_flight_display(flights: List[Dict], index: int) -> str:
    """Format single flight for display"""
    if index >= len(flights):
        return ""
    f = flights[index]
    return f"{f['departure_time']} -- {f['duration']} -- {f['arrival_time']}\nStarts at rs{f['price']}\nNon-stop\n{f['flight_number']}"

# Dispatcher: Route to correct agent based on current stage
def dispatcher(state: BookingState):
    """Routes to the correct agent based on booking stage"""
    current_agent = state.get("current_agent", "intent_agent")
    print(f"[DEBUG] dispatcher: current_agent={current_agent}, next_step={state.get('next_step')}")
    
    # If we're in the middle of a flow, continue from the next agent
    # Don't restart at intent_agent
    if current_agent not in ["intent_agent", "system"]:
        print(f"[DEBUG] Continuing from {current_agent}, routing to next_step")
        return state
    
    # First time - route to intent_agent
    print(f"[DEBUG] First time user, routing to intent_agent")
    return state

# Router for dispatcher
def dispatcher_router(state: BookingState) -> Literal["intent_agent", "collect_info", "search_flights", "select_flight", "confirmation", "payment"]:
    current_agent = state.get("current_agent", "intent_agent")
    next_step = state.get("next_step", "intent_agent")
    
    # If we already have a current agent and it's not the start, continue from next_step
    if current_agent not in ["intent_agent", "system"] and next_step:
        print(f"[DEBUG] dispatcher_router: returning {next_step}")
        return next_step
    
    # Start fresh
    print(f"[DEBUG] dispatcher_router: returning intent_agent")
    return "intent_agent"

# Agent 1: Intent & Greeting
def intent_agent(state: BookingState):
    """Handles initial greeting and intent detection"""
    print(f"[DEBUG] intent_agent called with {len(state['messages'])} messages")
    
    # Find the last user message (not assistant message)
    last_user_msg = None
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            last_user_msg = msg["content"]
            break
    
    if not last_user_msg:
        print("[DEBUG] No user message found, returning end")
        return {
            "messages": state["messages"],
            "current_agent": "intent_agent",
            "next_step": "end",
            "booking_data": state["booking_data"]
        }
    
    print(f"[DEBUG] Processing user message: {last_user_msg[:50]}")
    
    try:
        # Get greeting from LLM
        print("[DEBUG] Calling llm_call for INTENT_SYSTEM_PROMPT")
        response = llm_call(INTENT_SYSTEM_PROMPT, last_user_msg)
        print(f"[DEBUG] Got response: {response[:50]}")
        
        # Extract intent and entities
        print("[DEBUG] Extracting entities")
        entities = extract_entities(last_user_msg, state["booking_data"])
        print(f"[DEBUG] Entities: {entities}")
        
        # Update booking data with extracted info
        new_data = {**state["booking_data"]}
        for key, value in entities.items():
            if value is not None:
                new_data[key] = value
        
        # Determine next step
        if entities.get("intent") == "book_flight" or "book" in last_user_msg.lower():
            next_step = "collect_destination"
            print("[DEBUG] Book intent detected, going to collect_destination")
        else:
            next_step = "end"
            print("[DEBUG] No book intent, ending")
        
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": response}],
            "current_agent": "intent_agent",
            "next_step": next_step,
            "booking_data": new_data
        }
    except Exception as e:
        print(f"[ERROR] intent_agent failed: {e}")
        print(traceback.format_exc())
        raise

# Agent 2: Information Collection
def info_collection_agent(state: BookingState):
    """Collects destination, origin, dates, passengers"""
    print(f"[DEBUG] info_collection_agent called")
    
    try:
        # Find the last USER message (not assistant)
        last_user_msg = None
        for msg in reversed(state["messages"]):
            if msg.get("role") == "user":
                last_user_msg = msg["content"]
                break
        
        if not last_user_msg:
            print("[DEBUG] No user message found, returning collect_info")
            return {
                "messages": state["messages"],
                "current_agent": "info_collection_agent",
                "next_step": "collect_info",
                "booking_data": state["booking_data"]
            }
        
        print(f"[DEBUG] Last user message: {last_user_msg[:50]}")
        
        data = state["booking_data"]
        
        # Extract any new entities
        print("[DEBUG] Extracting entities from user message")
        entities = extract_entities(last_user_msg, data)
        print(f"[DEBUG] Extracted: {entities}")
        data.update({k: v for k, v in entities.items() if v is not None})
        
        # Map return_date to trip_type if it's one-way/round-trip
        if data.get("return_date") in ["one-way", "round-trip"] and not data.get("trip_type"):
            data["trip_type"] = data.get("return_date")
            print(f"[DEBUG] Mapped return_date to trip_type: {data['trip_type']}")
        
        # Determine what's missing
        print("[DEBUG] Creating IndigoDB")
        db = IndigoDB()
        
        print(f"[DEBUG] Getting airport names for origin={data.get('origin')}, dest={data.get('destination')}")
        origin_airport = db.get_airport_name(data.get("origin", ""))
        dest_airport = db.get_airport_name(data.get("destination", ""))
        print(f"[DEBUG] Airports: {origin_airport}, {dest_airport}")
        
        # Format dates for display
        travel_date = data.get("travel_date", "")
        try:
            dt = datetime.strptime(travel_date, "%Y-%m-%d")
            date_display = dt.strftime("%d %B %Y")
        except:
            date_display = travel_date
        
        children = data.get("children", 0)
        children_text = f", {children} Child" if children > 0 else ""
        
        # Build prompt with current state
        print("[DEBUG] Building info collection prompt")
        prompt = INFO_COLLECTION_PROMPT.format(
            destination=data.get("destination", ""),
            origin=data.get("origin", ""),
            travel_date=travel_date,
            trip_type=data.get("trip_type", ""),
            adults=data.get("adults", ""),
            children=children,
            origin_airport=origin_airport,
            dest_airport=dest_airport,
            travel_date_display=date_display,
            children_text=children_text
        )
        print("[DEBUG] Calling LLM for info collection")
        response = llm_call("You are a helpful airline booking assistant.", prompt)
        print(f"[DEBUG] Got response: {response[:50]}")
        
        # Check if we have all required info
        required = ["destination", "origin", "travel_date", "adults"]
        # trip_type is optional - if return_date is set, we have the trip type
        has_trip_type = data.get("trip_type") or data.get("return_date") in ["one-way", "round-trip"]
        
        missing = [f for f in required if not data.get(f)]
        if not has_trip_type:
            missing.append("trip_type")
        
        print(f"[DEBUG] Missing fields: {missing}")
        print(f"[DEBUG] Current data: destination={data.get('destination')}, origin={data.get('origin')}, travel_date={data.get('travel_date')}, trip_type={data.get('trip_type')}, adults={data.get('adults')}")
        
        # Move to search if we have all required fields
        if not missing:
            next_step = "search_flights"
            print(f"[DEBUG] All fields collected, moving to search_flights")
        else:
            next_step = "collect_info"
            print(f"[DEBUG] Missing {missing}, staying in collect_info")
        
        print(f"[DEBUG] info_collection_agent next_step: {next_step}")
        
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": response}],
            "current_agent": "info_collection_agent",
            "next_step": next_step,
            "booking_data": data
        }
    except Exception as e:
        print(f"[ERROR] info_collection_agent failed: {e}")
        print(traceback.format_exc())
        raise

# Agent 3: Flight Search
def flight_search_agent(state: BookingState):
    """Queries database and presents flights"""
    data = state["booking_data"]
    db = IndigoDB()
    
    flights = db.get_flights(
        data.get("origin", ""),
        data.get("destination", ""),
        data.get("travel_date", "")
    )
    
    if not flights:
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": "Sorry, no flights available. Please try different dates."}],
            "next_step": "collect_info",
            "search_results": []
        }
    
    # Format flights for display
    try:
        dt = datetime.strptime(data["travel_date"], "%Y-%m-%d")
        date_display = dt.strftime("%d %B %Y")
    except:
        date_display = data["travel_date"]
    
    flight_text = "Congratulations you are receiving a discounted fare by Indigo with our 6Exclusive offer..\n\n"
    flight_text += f"I found these onward flights for you on {date_display}\n\n"
    
    for i, flight in enumerate(flights[:12], 1):
        flight_text += f"-----\nFlight {i}\n"
        flight_text += f"{flight['departure_time']} -- {flight['duration']} -- {flight['arrival_time']}\n"
        flight_text += f"Starts at rs{flight['price']}\n"
        flight_text += f"Non-stop\n"
        flight_text += f"{flight['flight_number']}\n-----\n\n"
    
    flight_text += "Choose the onward flight you wish to book.\neg. flight 1, cheapest flight, 9:00AM"
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": flight_text}],
        "current_agent": "flight_search_agent",
        "next_step": "select_flight",
        "search_results": flights
    }

# Agent 4: Selection & Validation
def selection_agent(state: BookingState):
    """Handles flight selection and confirmation"""
    print("[DEBUG] selection_agent called")
    
    # Find the last USER message
    last_user_msg = None
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            last_user_msg = msg["content"].lower()
            break
    
    if not last_user_msg:
        print("[DEBUG] No user message in selection_agent")
        return {
            "messages": state["messages"],
            "next_step": "select_flight"
        }
    
    flights = state["search_results"]
    data = state["booking_data"]
    
    # Parse selection
    selected = None
    if "flight 1" in last_user_msg or "1" in last_user_msg:
        selected = flights[0] if flights else None
    elif "flight 2" in last_user_msg or "2" in last_user_msg:
        selected = flights[1] if len(flights) > 1 else None
    elif "cheapest" in last_user_msg:
        selected = min(flights, key=lambda x: x['price'])
    else:
        # Try flight number match
        for f in flights:
            if f['flight_number'].lower() in last_user_msg:
                selected = f
                break
    
    if not selected:
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": "Please select a valid flight (e.g., 'Flight 1' or 'cheapest')"}],
            "next_step": "select_flight"
        }
    
    db = IndigoDB()
    origin_airport = db.get_airport_name(selected['origin'])
    dest_airport = db.get_airport_name(selected['destination'])
    
    try:
        dt = datetime.strptime(data["travel_date"], "%Y-%m-%d")
        date_display = dt.strftime("%d %B %Y")
    except:
        date_display = data["travel_date"]
    
    response = f"""Please review onward flight details
Departure: ({origin_airport}) {selected['origin']}
Destination: {dest_airport} ({selected['destination']})
Travel Date: {date_display}
{selected['departure_time']} -- {selected['duration']} -- {selected['arrival_time']}
Starts at rs{selected['price']}
Non-stop
{selected['flight_number']}

Please review and confirm your Indigo {selected['flight_number']} flight
Option[Yes]
Option[No]"""
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": response}],
        "current_agent": "selection_agent",
        "next_step": "confirmation",
        "selected_flight": selected,
        "confirmation_step": "flight_confirm"
    }

# Agent 5: Confirmation Flow (Multi-step)
def confirmation_agent(state: BookingState):
    """Handles confirmations, WhatsApp consent, passenger details"""
    print("[DEBUG] confirmation_agent called")
    
    # Find the last USER message
    last_user_msg = None
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            last_user_msg = msg["content"].lower()
            break
    
    if not last_user_msg:
        print("[DEBUG] No user message in confirmation_agent")
        step = state.get("confirmation_step", "flight_confirm")
        return {
            "messages": state["messages"],
            "next_step": "confirmation",
            "confirmation_step": step
        }
    
    step = state.get("confirmation_step", "flight_confirm")
    data = state["booking_data"]
    
    if step == "flight_confirm":
        if "yes" in last_user_msg:
            response = llm_call("You are a booking assistant.", WHATSAPP_PROMPT)
            return {
                "messages": state["messages"] + [{"role": "assistant", "content": response}],
                "current_agent": "confirmation_agent",
                "next_step": "confirmation",
                "confirmation_step": "whatsapp_consent"
            }
        else:
            return {"next_step": "collect_info"}
    
    elif step == "whatsapp_consent":
        consent = "yes" in last_user_msg
        data["whatsapp_consent"] = consent
        response = llm_call("You are a booking assistant.", PASSENGER_PROMPT)
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": response}],
            "booking_data": data,
            "current_agent": "confirmation_agent",
            "next_step": "confirmation",
            "confirmation_step": "collect_names"
        }
    
    elif step == "collect_names":
        # Extract names using simple extraction or store as-is
        entities = extract_entities(last_user_msg, {})
        if entities.get("passenger_names"):
            data["passenger_names"] = entities["passenger_names"]
        else:
            data["passenger_names"] = last_user_msg
        
        response = llm_call("You are a booking assistant.", EMAIL_PROMPT)
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": response}],
            "booking_data": data,
            "current_agent": "confirmation_agent",
            "next_step": "confirmation",
            "confirmation_step": "collect_email"
        }
    
    elif step == "collect_email":
        data["email"] = last_user_msg
        return {
            "booking_data": data,
            "current_agent": "confirmation_agent",
            "next_step": "payment",
            "confirmation_step": "complete"
        }
    
    return {"next_step": "payment"}

# Agent 6: Payment & Summary
def payment_agent(state: BookingState):
    """Generates final booking summary"""
    data = state["booking_data"]
    flight = state["selected_flight"]
    
    total = flight["price"] * data.get("adults", 1)
    
    try:
        dt = datetime.strptime(data["travel_date"], "%Y-%m-%d")
        date_display = dt.strftime("%d-%m-%Y")
    except:
        date_display = data["travel_date"]
    
    response = PAYMENT_PROMPT.format(
        origin=data["origin"],
        destination=data["destination"],
        travel_date=date_display,
        passenger_name=data.get("passenger_names", ""),
        flight_number=flight["flight_number"],
        departure=flight["departure_time"],
        arrival=flight["arrival_time"],
        duration=flight["duration"],
        adults=data.get("adults", 1),
        price=flight["price"],
        total=total
    )
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": response}],
        "current_agent": "payment_agent",
        "next_step": "end"
    }

# Router function
def router(state: BookingState) -> Literal["intent_agent", "collect_info", "search_flights", "select_flight", "confirmation", "payment", "end"]:
    return state.get("next_step", "end")

# Build the graph
def create_booking_graph():
    workflow = StateGraph(BookingState)
    
    # Add dispatcher node first
    workflow.add_node("dispatcher", dispatcher)
    
    # Add nodes
    workflow.add_node("intent_agent", intent_agent)
    workflow.add_node("collect_info", info_collection_agent)
    workflow.add_node("search_flights", flight_search_agent)
    workflow.add_node("select_flight", selection_agent)
    workflow.add_node("confirmation", confirmation_agent)
    workflow.add_node("payment", payment_agent)
    
    # Entry point is dispatcher
    workflow.set_entry_point("dispatcher")
    
    # Dispatcher routes to the correct agent
    workflow.add_conditional_edges("dispatcher", dispatcher_router, {
        "intent_agent": "intent_agent",
        "collect_info": "collect_info",
        "search_flights": "search_flights",
        "select_flight": "select_flight",
        "confirmation": "confirmation",
        "payment": "payment"
    })
    
    # Add conditional edges
    workflow.add_conditional_edges("intent_agent", router, {
        "intent_agent": END,
        "collect_destination": "collect_info",
        "collect_info": "collect_info",
        "search_flights": "search_flights",
        "select_flight": "select_flight",
        "confirmation": "confirmation",
        "payment": "payment",
        "end": END
    })
    
    workflow.add_conditional_edges("collect_info", router, {
        "collect_info": END,
        "search_flights": "search_flights",
        "end": END
    })
    
    workflow.add_conditional_edges("search_flights", router, {
        "select_flight": "select_flight",
        "collect_info": END
    })
    
    workflow.add_conditional_edges("select_flight", router, {
        "select_flight": END,
        "confirmation": "confirmation"
    })
    
    workflow.add_conditional_edges("confirmation", router, {
        "confirmation": END,
        "payment": "payment",
        "collect_info": "collect_info"
    })
    
    workflow.add_conditional_edges("payment", router, {
        "end": END
    })
    
    return workflow.compile()

# Create graph instance
graph = create_booking_graph()