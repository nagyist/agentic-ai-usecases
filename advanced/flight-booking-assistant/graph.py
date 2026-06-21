import logging
from langgraph.graph import StateGraph, END

from state import BookingState
from nodes.router import route
from nodes.information_extractor import extract_information
from nodes.confirmation import confirm_intent
from nodes.flight_selection import select_flight
from nodes.city_lookup import lookup_cities
from nodes.conversation_driver import drive_conversation
from nodes.slot_validator import validate_slots
from nodes.payment import build_payment_summary
from nodes.done import done
from services.flight_search import flight_search_agent
from services.pnr_lookup import pnr_lookup_agent
from constants import Intent, Process, Step

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dispatcher — entry point, routes every turn to the right starting node
# ---------------------------------------------------------------------------

PNR_PROCESSES = {Process.WEB_CHECKIN, Process.FLIGHT_STATUS}

_STEP_TO_NODE = {
    Step.DONE:             "done",
    Step.SHOW_FLIGHTS:     "select",
    Step.CONFIRM_BOOKING:  "confirm",
    Step.PAYMENT:          "payment",
    Step.COLLECT_PNR:      "info_extractor",
    Step.FLIGHT_CONFIRM:   "info_extractor",
    Step.WHATSAPP_CONSENT: "info_extractor",
    Step.COLLECT_NAMES:    "info_extractor",
    Step.COLLECT_EMAIL:    "info_extractor",
}


def dispatch_route(state: BookingState) -> str:
    step = state.get("step", Step.GREETING)
    logger.debug("dispatch_route: step=%s", step)
    return _STEP_TO_NODE.get(step, "router")


# ---------------------------------------------------------------------------
# Routing after each node
# ---------------------------------------------------------------------------

def route_after_router(state: BookingState) -> str:
    intent = state.get("intent", "")
    if intent == Intent.BOOK_FLIGHT:
        return "info_extractor"
    if intent in (Intent.WEB_CHECKIN, Intent.FLIGHT_STATUS):
        return "conversation_driver"
    return END


def route_after_info_extractor(state: BookingState) -> str:
    if state.get("process") in PNR_PROCESSES:
        return "pnr_lookup"
    if state.get("step") == Step.EXTRACTED:
        return "validate_slots"
    return "conversation_driver"


def route_after_validate_slots(state: BookingState) -> str:
    if state.get("slot_error"):
        return "conversation_driver"
    if state.get("cities_updated"):
        return "city_lookup"
    return "conversation_driver"


def route_after_conversation_driver(state: BookingState) -> str:
    if state.get("terminated"):
        return END
    if state.get("step") == Step.PAYMENT:
        return "payment"
    if state.get("step") == Step.SEARCH_RETURN_FLIGHTS:
        return "search"
    return END


def route_after_confirmation(state: BookingState) -> str:
    step = state.get("step", "")
    if step == Step.SEARCH_FLIGHTS:
        return "search"
    if step == Step.COLLECT_SLOTS:
        return "info_extractor"
    return END


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def create_graph():
    g = StateGraph(BookingState)

    g.add_node("router",              route)
    g.add_node("info_extractor",      extract_information)
    g.add_node("validate_slots",      validate_slots)
    g.add_node("city_lookup",         lookup_cities)
    g.add_node("conversation_driver", drive_conversation)
    g.add_node("confirm",             confirm_intent)
    g.add_node("search",              flight_search_agent)
    g.add_node("select",              select_flight)
    g.add_node("payment",             build_payment_summary)
    g.add_node("pnr_lookup",          pnr_lookup_agent)
    g.add_node("done",                done)

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
        END:                   END,
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

    g.add_edge("city_lookup", "conversation_driver")

    g.add_conditional_edges("conversation_driver", route_after_conversation_driver, {
        "payment": "payment",
        "search":  "search",
        END:       END,
    })

    g.add_edge("pnr_lookup", END)

    g.add_conditional_edges("confirm", route_after_confirmation, {
        "search":         "search",
        "info_extractor": "info_extractor",
        END:              END,
    })

    g.add_edge("search",  END)
    g.add_edge("select",  END)
    g.add_edge("payment", END)
    g.add_edge("done",    END)

    return g.compile()


booking_graph = create_graph()
