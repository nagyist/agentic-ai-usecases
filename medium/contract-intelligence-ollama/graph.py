from langgraph.graph import StateGraph, END

from models.state import ContractState
from nodes.preprocessing import preprocess_node
from nodes.ocr_extraction import ocr_extraction_node
from nodes.language_detection import detect_language_node
from nodes.translation import translation_node
from nodes.indexing import indexing_node
from nodes.extraction_agent import extraction_agent_node
from nodes.excel_generation import excel_generation_node


def _route_after_language(state: ContractState) -> str:
    return "translate" if state.get("requires_translation") else "index"


def build_graph():
    g = StateGraph(ContractState)

    g.add_node("preprocess", preprocess_node)
    g.add_node("ocr_extract", ocr_extraction_node)
    g.add_node("detect_language", detect_language_node)
    g.add_node("translate", translation_node)
    g.add_node("index", indexing_node)
    g.add_node("extract", extraction_agent_node)
    g.add_node("generate_excel", excel_generation_node)

    g.set_entry_point("preprocess")
    g.add_edge("preprocess", "ocr_extract")
    g.add_edge("ocr_extract", "detect_language")
    g.add_conditional_edges(
        "detect_language",
        _route_after_language,
        {"translate": "translate", "index": "index"},
    )
    g.add_edge("translate", "index")
    g.add_edge("index", "extract")
    g.add_edge("extract", "generate_excel")
    g.add_edge("generate_excel", END)

    return g.compile()


# Singleton – imported by app.py
contract_graph = build_graph()
