from langgraph.graph import StateGraph, END

from state import BookingState
from nodes.conversation_driver import drive_conversation
from nodes.information_extractor import extract_information
from services.pnr_lookup import pnr_lookup_agent
from constants import Step, Process

_PNR_PROCESSES = {Process.WEB_CHECKIN, Process.FLIGHT_STATUS}


def _dispatch(state: BookingState) -> str:
    # Resume mid-collection if PNR is already being gathered
    if state.get("step") == Step.COLLECT_PNR:
        return "info_extractor"
    return "conversation_driver"


def _after_info_extractor(state: BookingState) -> str:
    if state.get("process") in _PNR_PROCESSES and state.get("pnr"):
        return "pnr_lookup"
    return "conversation_driver"


def create_pnr_graph():
    g = StateGraph(BookingState)

    g.add_node("conversation_driver", drive_conversation)
    g.add_node("info_extractor",      extract_information)
    g.add_node("pnr_lookup",          pnr_lookup_agent)

    g.set_conditional_entry_point(_dispatch, {
        "conversation_driver": "conversation_driver",
        "info_extractor":      "info_extractor",
    })

    g.add_edge("conversation_driver", "info_extractor")

    g.add_conditional_edges("info_extractor", _after_info_extractor, {
        "pnr_lookup":          "pnr_lookup",
        "conversation_driver": "conversation_driver",
    })

    g.add_edge("pnr_lookup", END)

    return g.compile()


pnr_subgraph = create_pnr_graph()
