import time
from langgraph.graph import StateGraph, END

from state import BookingState
from agents.router import router_agent
from agents.information_extractor import information_extractor_agent
from agents.conversation_driver import conversation_driver_agent
from agents.confirmation import confirmation_agent
from agents.flight_selection import flight_selection_agent
from agents.payment import payment_agent
from agents.pnr_lookup import pnr_lookup_agent
from agents.city_lookup import city_lookup_agent
from agents.slot_validator import validate_slots_agent
from utils.db import fetch_flights
from utils.llm import log_node

# ---------------------------------------------------------------------------
# Search node (inline — pure data fetch)
# ---------------------------------------------------------------------------

def search_flights_node(state: dict) -> dict:
    print(f"\n[DEBUG] search_flights_node called")
    t0 = time.time()

    booking_leg = state.get("booking_leg") or "outbound"
    if booking_leg == "return":
        departure = state.get("destination_city", "")
        destination = state.get("departure_city", "")
        search_date = state.get("return_date", "")
    else:
        departure = state.get("departure_city", "")
        destination = state.get("destination_city", "")
        search_date = state.get("travel_date", "")

    flights = fetch_flights(departure, destination)

    if not flights:
        latency_ms = round((time.time() - t0) * 1000)
        log_node("search_flights", {
            "route": f"{departure} → {destination}",
            "travel_date": search_date,
            "flights_found": 0,
            "outcome": "no_flights",
        }, latency_ms=latency_ms)
        state["assistant_message"] = (
            "Sorry, no flights found for that route and date. "
            "Please try a different date or route."
        )
        state["step"] = "COLLECT_SLOTS"
        state["current_agent"] = "search"
        return state

    try:
        from datetime import datetime
        dt = datetime.strptime(search_date, "%Y-%m-%d")
        date_display = dt.strftime("%d %B %Y")
    except Exception:
        date_display = search_date

    leg_label = "return flights" if booking_leg == "return" else "flights"
    text = (
        f"Congratulations! You are receiving a discounted fare with IndiGo's 6Exclusive offer.\n\n"
        f"Available {leg_label} on {date_display} ({departure} → {destination}):\n\n"
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
    log_node("search_flights", {
        "route": f"{departure} → {destination}",
        "travel_date": state.get("travel_date"),
        "flights_found": len(flights),
        "flight_numbers": [f["flight_number"] for f in flights],
        "outcome": "ok",
    }, latency_ms=round((time.time() - t0) * 1000))
    return state


# ---------------------------------------------------------------------------
# Done handler — shown after payment summary, resets for a fresh session
# ---------------------------------------------------------------------------

def done_handler(state: dict) -> dict:
    print(f"\n[DEBUG] done_handler called")
    state["assistant_message"] = (
        "Thank you for booking with IndiGo!\n"
        "You will receive your PNR via email and WhatsApp shortly.\n\n"
        "Is there anything else I can help you with?\n"
        "- Book a flight ticket\n"
        "- Flight Status\n"
        "- Web Check-in"
    )
    state["step"] = "SHOW_MENU"
    state["process"] = ""
    state["current_agent"] = "done"
    return state


# ---------------------------------------------------------------------------
# Dispatcher — entry point, routes every turn to the right starting node
# ---------------------------------------------------------------------------

PNR_PROCESSES = {"web_checkin", "flight_status"}


def dispatch_route(state: dict) -> str:
    step = state.get("step", "GREETING")
    print(f"[DEBUG] dispatch_route: step={step}")

    if step == "DONE":
        return "done"
    if step == "SHOW_FLIGHTS":
        return "select"
    if step == "CONFIRM_BOOKING":
        return "confirm"
    if step == "PAYMENT":
        return "payment"
    if step == "COLLECT_PNR":
        return "info_extractor"
    if step in ("flight_confirm", "whatsapp_consent", "collect_names", "collect_email"):
        return "info_extractor"
    # GREETING | SHOW_MENU | COLLECT_SLOTS | EXTRACTED | CITY_VALIDATED
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
    return END


def route_after_info_extractor(state: dict) -> str:
    process = state.get("process", "")
    if process in PNR_PROCESSES:
        return "pnr_lookup"
    if state.get("step") == "EXTRACTED":
        return "validate_slots"
    return "conversation_driver"


def route_after_validate_slots(state: dict) -> str:
    if state.get("slot_error"):
        return "conversation_driver"
    if state.get("cities_updated"):
        return "city_lookup"
    return "conversation_driver"


def route_after_city_lookup(_) -> str:
    return "conversation_driver"


def route_after_conversation_driver(state: dict) -> str:
    if state.get("terminated"):
        return END
    if state.get("step") == "PAYMENT":
        return "payment"
    if state.get("step") == "SEARCH_RETURN_FLIGHTS":
        return "search"
    return END


def route_after_pnr_lookup(_) -> str:
    return END


def route_after_confirmation(state: dict) -> str:
    step = state.get("step", "")
    if step == "SEARCH_FLIGHTS":
        return "search"
    if step == "COLLECT_SLOTS":
        return "info_extractor"
    return END


def route_after_search(_) -> str:
    return END


def route_after_select(_) -> str:
    return END


def route_after_payment(_) -> str:
    return END


def route_after_done(_) -> str:
    return END

# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def create_graph():
    g = StateGraph(BookingState)

    g.add_node("router", router_agent)
    g.add_node("info_extractor", information_extractor_agent)
    g.add_node("validate_slots", validate_slots_agent)
    g.add_node("city_lookup", city_lookup_agent)
    g.add_node("conversation_driver", conversation_driver_agent)
    g.add_node("confirm", confirmation_agent)
    g.add_node("search", search_flights_node)
    g.add_node("select", flight_selection_agent)
    g.add_node("payment", payment_agent)
    g.add_node("pnr_lookup", pnr_lookup_agent)
    g.add_node("done", done_handler)

    g.set_conditional_entry_point(dispatch_route, {
        "router":         "router",
        "info_extractor": "info_extractor",
        "confirm":        "confirm",
        "select":         "select",
        "payment":        "payment",
        "done":           "done",
    })

    g.add_conditional_edges("router", route_after_router, {
        "info_extractor":      "info_extractor",
        "conversation_driver": "conversation_driver",
        END: END,
    })

    g.add_conditional_edges("info_extractor", route_after_info_extractor, {
        "validate_slots":      "validate_slots",
        "pnr_lookup":          "pnr_lookup",
        "conversation_driver": "conversation_driver",
    })

    g.add_conditional_edges("validate_slots", route_after_validate_slots, {
        "city_lookup":         "city_lookup",
        "conversation_driver": "conversation_driver",
    })

    g.add_conditional_edges("city_lookup", route_after_city_lookup, {
        "conversation_driver": "conversation_driver",
    })

    g.add_conditional_edges("conversation_driver", route_after_conversation_driver, {
        "payment": "payment",
        "search":  "search",
        END: END,
    })

    g.add_conditional_edges("pnr_lookup", route_after_pnr_lookup, {
        END: END,
    })

    g.add_conditional_edges("confirm", route_after_confirmation, {
        "search":         "search",
        "info_extractor": "info_extractor",
        END: END,
    })

    g.add_conditional_edges("search", route_after_search, {
        END: END,
    })

    g.add_conditional_edges("select", route_after_select, {
        END: END,
    })

    g.add_conditional_edges("payment", route_after_payment, {
        END: END,
    })

    g.add_conditional_edges("done", route_after_done, {
        END: END,
    })

    return g.compile()


booking_graph = create_graph()
