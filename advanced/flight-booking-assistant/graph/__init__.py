import logging
from langgraph.graph import StateGraph, END

from state import BookingState
from nodes.router import route
from .booking_subgraph import booking_subgraph
from .pnr_subgraph import pnr_subgraph
from constants import Intent, Step

logger = logging.getLogger(__name__)

_BOOKING_STEPS = {
    Step.COLLECT_SLOTS, Step.EXTRACTED, Step.CITY_VALIDATED,
    Step.CONFIRM_BOOKING, Step.SEARCH_FLIGHTS, Step.SEARCH_RETURN_FLIGHTS,
    Step.SHOW_FLIGHTS, Step.FLIGHT_CONFIRM, Step.WHATSAPP_CONSENT,
    Step.COLLECT_NAMES, Step.COLLECT_EMAIL, Step.PAYMENT, Step.DONE,
}

_PNR_STEPS = {Step.COLLECT_PNR}


def dispatch_route(state: BookingState) -> str:
    step = state.get("step", Step.GREETING)
    logger.debug("dispatch_route: step=%s", step)
    if step in _BOOKING_STEPS:
        return "booking"
    if step in _PNR_STEPS:
        return "pnr"
    return "router"


def route_after_router(state: BookingState) -> str:
    intent = state.get("intent", "")
    if intent == Intent.BOOK_FLIGHT:
        return "booking"
    if intent in (Intent.WEB_CHECKIN, Intent.FLIGHT_STATUS):
        return "pnr"
    return END


def create_graph():
    g = StateGraph(BookingState)

    g.add_node("router",  route)
    g.add_node("booking", booking_subgraph)
    g.add_node("pnr",     pnr_subgraph)

    g.set_conditional_entry_point(dispatch_route, {
        "router":  "router",
        "booking": "booking",
        "pnr":     "pnr",
    })

    g.add_conditional_edges("router", route_after_router, {
        "booking": "booking",
        "pnr":     "pnr",
        END:       END,
    })

    g.add_edge("booking", END)
    g.add_edge("pnr",     END)

    return g.compile()


booking_graph = create_graph()
