from langgraph.graph import StateGraph, END

from state import BookingState
from nodes.information_extractor import extract_information
from nodes.slot_validator import validate_slots
from nodes.city_lookup import lookup_cities
from nodes.conversation_driver import drive_conversation
from nodes.confirmation import confirm_intent
from nodes.flight_selection import select_flight
from nodes.payment import build_payment_summary
from nodes.done import done
from services.flight_search import flight_search_agent
from constants import Step

_STEP_TO_NODE = {
    Step.SHOW_FLIGHTS:     "select",
    Step.CONFIRM_BOOKING:  "confirm",
    Step.PAYMENT:          "payment",
    Step.DONE:             "done",
    Step.FLIGHT_CONFIRM:   "info_extractor",
    Step.WHATSAPP_CONSENT: "info_extractor",
    Step.COLLECT_NAMES:    "info_extractor",
    Step.COLLECT_EMAIL:    "info_extractor",
}


def _dispatch(state: BookingState) -> str:
    return _STEP_TO_NODE.get(state.get("step", ""), "info_extractor")


def _after_info_extractor(state: BookingState) -> str:
    if state.get("step") == Step.EXTRACTED:
        return "validate_slots"
    return "conversation_driver"


def _after_validate_slots(state: BookingState) -> str:
    if state.get("slot_error"):
        return "conversation_driver"
    if state.get("cities_updated"):
        return "city_lookup"
    return "conversation_driver"


def _after_conversation_driver(state: BookingState) -> str:
    if state.get("terminated"):
        return END
    if state.get("step") == Step.PAYMENT:
        return "payment"
    if state.get("step") in (Step.SEARCH_FLIGHTS, Step.SEARCH_RETURN_FLIGHTS):
        return "search"
    return END


def _after_confirmation(state: BookingState) -> str:
    step = state.get("step", "")
    if step in (Step.SEARCH_FLIGHTS, Step.SEARCH_RETURN_FLIGHTS):
        return "search"
    if step == Step.COLLECT_SLOTS:
        return "info_extractor"
    return END


def create_booking_graph():
    g = StateGraph(BookingState)

    g.add_node("info_extractor",      extract_information)
    g.add_node("validate_slots",      validate_slots)
    g.add_node("city_lookup",         lookup_cities)
    g.add_node("conversation_driver", drive_conversation)
    g.add_node("confirm",             confirm_intent)
    g.add_node("search",              flight_search_agent)
    g.add_node("select",              select_flight)
    g.add_node("payment",             build_payment_summary)
    g.add_node("done",                done)

    g.set_conditional_entry_point(_dispatch, {
        "info_extractor": "info_extractor",
        "select":         "select",
        "confirm":        "confirm",
        "payment":        "payment",
        "done":           "done",
    })

    g.add_conditional_edges("info_extractor", _after_info_extractor, {
        "validate_slots":      "validate_slots",
        "conversation_driver": "conversation_driver",
    })

    g.add_conditional_edges("validate_slots", _after_validate_slots, {
        "city_lookup":         "city_lookup",
        "conversation_driver": "conversation_driver",
    })

    g.add_edge("city_lookup", "conversation_driver")

    g.add_conditional_edges("conversation_driver", _after_conversation_driver, {
        "payment": "payment",
        "search":  "search",
        END:       END,
    })

    g.add_conditional_edges("confirm", _after_confirmation, {
        "search":         "search",
        "info_extractor": "info_extractor",
        END:              END,
    })

    g.add_edge("search",  END)
    g.add_edge("select",  END)
    g.add_edge("payment", END)
    g.add_edge("done",    END)

    return g.compile()


booking_subgraph = create_booking_graph()
