from langgraph.graph import StateGraph, END

from state import BookingState
from agents.greeting import greeting_agent
from agents.information_extractor import information_extractor_agent
from agents.conversation_driver import conversation_driver_agent
from agents.confirmation import confirmation_agent
from agents.flight_selection import flight_selection_agent
from agents.post_confirmation import post_confirmation_agent
from agents.payment import payment_agent
from utils.db import fetch_flights

# ---------------------------------------------------------------------------
# Search node (inline — no agent file needed, pure data fetch)
# ---------------------------------------------------------------------------

def search_flights_node(state: dict) -> dict:
    print(f"\n[DEBUG] search_flights_node called")
    flights = fetch_flights(
        state.get("departure_city", ""),
        state.get("destination_city", ""),
        state.get("travel_date", ""),
    )

    if not flights:
        state["assistant_message"] = (
            "Sorry, no flights found for that route and date. "
            "Please try a different date or route."
        )
        state["step"] = "COLLECT_SLOTS"
        state["current_agent"] = "search"
        return state

    # Format flight list for display
    try:
        from datetime import datetime
        dt = datetime.strptime(state["travel_date"], "%Y-%m-%d")
        date_display = dt.strftime("%d %B %Y")
    except Exception:
        date_display = state.get("travel_date", "")

    text = (
        "Congratulations! You are receiving a discounted fare with IndiGo's 6Exclusive offer.\n\n"
        f"Available flights on {date_display}:\n\n"
    )
    for i, f in enumerate(flights, 1):
        text += (
            f"-----\nFlight {i}\n"
            f"{f['departure_time']} -- {f['duration']} -- {f['arrival_time']}\n"
            f"Starts at Rs.{f['price']}\n"
            f"Non-stop\n"
            f"{f['flight_number']}\n"
            f"-----\n\n"
        )
    text += "Please choose the flight you wish to book.\neg. flight 1, cheapest flight, 9:00 AM"

    state["flights"] = flights
    state["assistant_message"] = text
    state["step"] = "SHOW_FLIGHTS"
    state["current_agent"] = "search"
    return state

# ---------------------------------------------------------------------------
# Dispatcher — entry point, routes every turn to the right starting node
# ---------------------------------------------------------------------------

POST_CONFIRM_STEPS = {"flight_confirm", "whatsapp_consent", "collect_names", "collect_email"}


def dispatcher(state: dict) -> dict:
    return state


def dispatch_route(state: dict) -> str:
    step = state.get("step", "GREETING")
    print(f"[DEBUG] dispatch_route: step={step}")

    if step in POST_CONFIRM_STEPS:
        return "post_confirm"
    if step == "SHOW_FLIGHTS":
        return "select"
    if step == "CONFIRM_BOOKING":
        return "confirm"
    if step == "PAYMENT":
        return "payment"
    # GREETING | SHOW_MENU | COLLECT_SLOTS | EXTRACTED | SEARCH_FLIGHTS | default
    return "greeting"

# ---------------------------------------------------------------------------
# Routing after each node
# ---------------------------------------------------------------------------

def route_after_greeting(state: dict) -> str:
    step = state.get("step", "")
    # Greeting showed the menu — stop here and wait for user
    if step == "SHOW_MENU":
        return END
    # User wants to book — run extraction then slot collection
    return "info_extractor"


def route_after_info_extractor(state: dict) -> str:
    return "conversation_driver"


def route_after_conversation_driver(state: dict) -> str:
    step = state.get("step", "")
    if step == "CONFIRM_BOOKING":
        # Stop — show booking summary, wait for yes/no
        return END
    # Still collecting — stop and wait for next user message
    return END


def route_after_confirmation(state: dict) -> str:
    step = state.get("step", "")
    if step == "SEARCH_FLIGHTS":
        return "search"
    # No or ambiguous — stop and wait
    return END


def route_after_search(state: dict) -> str:
    # Always stop after showing flights — wait for user to pick one
    return END


def route_after_select(state: dict) -> str:
    # Always stop after showing selected flight details — wait for yes/no
    return END


def route_after_post_confirm(state: dict) -> str:
    step = state.get("step", "")
    if step == "PAYMENT":
        return "payment"
    return END


def route_after_payment(state: dict) -> str:
    return END

# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def create_graph():
    g = StateGraph(BookingState)

    g.add_node("dispatcher", dispatcher)
    g.add_node("greeting", greeting_agent)
    g.add_node("info_extractor", information_extractor_agent)
    g.add_node("conversation_driver", conversation_driver_agent)
    g.add_node("confirm", confirmation_agent)
    g.add_node("search", search_flights_node)
    g.add_node("select", flight_selection_agent)
    g.add_node("post_confirm", post_confirmation_agent)
    g.add_node("payment", payment_agent)

    g.set_entry_point("dispatcher")

    g.add_conditional_edges("dispatcher", dispatch_route, {
        "greeting": "greeting",
        "confirm": "confirm",
        "select": "select",
        "post_confirm": "post_confirm",
        "payment": "payment",
    })

    g.add_conditional_edges("greeting", route_after_greeting, {
        "info_extractor": "info_extractor",
        END: END,
    })

    g.add_conditional_edges("info_extractor", route_after_info_extractor, {
        "conversation_driver": "conversation_driver",
    })

    g.add_conditional_edges("conversation_driver", route_after_conversation_driver, {
        END: END,
    })

    g.add_conditional_edges("confirm", route_after_confirmation, {
        "search": "search",
        END: END,
    })

    g.add_conditional_edges("search", route_after_search, {
        END: END,
    })

    g.add_conditional_edges("select", route_after_select, {
        END: END,
    })

    g.add_conditional_edges("post_confirm", route_after_post_confirm, {
        "payment": "payment",
        END: END,
    })

    g.add_conditional_edges("payment", route_after_payment, {
        END: END,
    })

    return g.compile()


booking_graph = create_graph()
