from langgraph.graph import StateGraph, END

from state import BookingState
from agents.router import router_agent
from agents.information_extractor import information_extractor_agent
from agents.conversation_driver import conversation_driver_agent
from agents.confirmation import confirmation_agent
from agents.flight_selection import flight_selection_agent
from agents.post_confirmation import post_confirmation_agent
from agents.payment import payment_agent
from agents.pnr_lookup import pnr_lookup_agent
from agents.city_lookup import city_lookup_agent
from utils.db import fetch_flights

# ---------------------------------------------------------------------------
# Search node (inline — no agent file needed, pure data fetch)
# ---------------------------------------------------------------------------

def search_flights_node(state: dict) -> dict:
    print(f"\n[DEBUG] search_flights_node called")
    flights = fetch_flights(
        state.get("departure_city", ""),
        state.get("destination_city", ""),
    )

    if not flights:
        state["assistant_message"] = (
            "Sorry, no flights found for that route and date. "
            "Please try a different date or route."
        )
        state["step"] = "COLLECT_SLOTS"
        state["current_agent"] = "search"
        return state

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
PNR_PROCESSES = {"web_checkin", "flight_status"}


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
    # When user is in a PNR process and provides their PNR, skip the router
    if step == "COLLECT_PNR":
        return "info_extractor"
    # GREETING | SHOW_MENU | COLLECT_SLOTS | EXTRACTED | SEARCH_FLIGHTS | default
    return "router"

# ---------------------------------------------------------------------------
# Routing after each node
# ---------------------------------------------------------------------------

def route_after_router(state: dict) -> str:
    intent = state.get("intent", "")
    if intent == "book_flight":
        return "info_extractor"
    if intent in ("web_checkin", "flight_status"):
        return "conversation_driver"
    # "greeting", "out_of_scope", or process-switch block — response already set
    return END


def route_after_info_extractor(state: dict) -> str:
    process = state.get("process", "")
    if process in PNR_PROCESSES:
        return "pnr_lookup"
    if state.get("cities_updated"):
        return "city_lookup"
    return "conversation_driver"


def route_after_city_lookup(state: dict) -> str:
    return "conversation_driver"


def route_after_conversation_driver(state: dict) -> str:
    step = state.get("step", "")
    if step == "CONFIRM_BOOKING":
        return END
    return END


def route_after_pnr_lookup(state: dict) -> str:
    return END


def route_after_confirmation(state: dict) -> str:
    step = state.get("step", "")
    if step == "SEARCH_FLIGHTS":
        return "search"
    return END


def route_after_search(state: dict) -> str:
    return END


def route_after_select(state: dict) -> str:
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

    g.add_node("router", router_agent)
    g.add_node("info_extractor", information_extractor_agent)
    g.add_node("city_lookup", city_lookup_agent)
    g.add_node("conversation_driver", conversation_driver_agent)
    g.add_node("confirm", confirmation_agent)
    g.add_node("search", search_flights_node)
    g.add_node("select", flight_selection_agent)
    g.add_node("post_confirm", post_confirmation_agent)
    g.add_node("payment", payment_agent)
    g.add_node("pnr_lookup", pnr_lookup_agent)

    g.set_conditional_entry_point(dispatch_route, {
        "router":         "router",
        "info_extractor": "info_extractor",
        "confirm":        "confirm",
        "select":         "select",
        "post_confirm":   "post_confirm",
        "payment":        "payment",
    })

    g.add_conditional_edges("router", route_after_router, {
        "info_extractor":     "info_extractor",
        "conversation_driver": "conversation_driver",
        END: END,
    })

    g.add_conditional_edges("info_extractor", route_after_info_extractor, {
        "city_lookup":         "city_lookup",
        "pnr_lookup":          "pnr_lookup",
        "conversation_driver": "conversation_driver",
    })

    g.add_conditional_edges("city_lookup", route_after_city_lookup, {
        "conversation_driver": "conversation_driver",
    })

    g.add_conditional_edges("conversation_driver", route_after_conversation_driver, {
        END: END,
    })

    g.add_conditional_edges("pnr_lookup", route_after_pnr_lookup, {
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
