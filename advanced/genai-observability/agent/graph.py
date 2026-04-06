# agent/graph.py
# ─────────────────────────────────────────────────────────────────────────────
# LangGraph graph definition.
#
# Graph topology:
#
#   [START]
#     │
#     ▼
#   router_node
#     │
#     ├── "sql"        ──▶ sql_node        ──┐
#     ├── "rag"        ──▶ rag_node        ──┤
#     └── "web_search" ──▶ web_search_node ──┤
#                                            │
#                                            ▼
#                                      synthesise_node
#                                            │
#                                            ▼
#                                     update_history_node
#                                            │
#                                          [END]
# ─────────────────────────────────────────────────────────────────────────────

from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    router_node,
    sql_node,
    rag_node,
    web_search_node,
    synthesise_node,
    update_history_node,
)


def _route_selector(state: dict) -> str:
    """Conditional edge: read state["route"] and return the target node name."""
    route = state.get("route", "web_search")
    return {
        "sql":        "sql_node",
        "rag":        "rag_node",
        "web_search": "web_search_node",
    }.get(route, "web_search_node")


def build_graph() -> StateGraph:
    """
    Assemble and compile the LangGraph routing agent.
    Returns a compiled graph ready to invoke.
    """
    graph = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    graph.add_node("router_node",       router_node)
    graph.add_node("sql_node",          sql_node)
    graph.add_node("rag_node",          rag_node)
    graph.add_node("web_search_node",   web_search_node)
    graph.add_node("synthesise_node",   synthesise_node)
    graph.add_node("update_history_node", update_history_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.set_entry_point("router_node")

    # ── Conditional routing: router → one of the three tool nodes ─────────────
    graph.add_conditional_edges(
        source="router_node",
        path=_route_selector,
        path_map={
            "sql_node":        "sql_node",
            "rag_node":        "rag_node",
            "web_search_node": "web_search_node",
        },
    )

    # ── All tool nodes feed into synthesis ────────────────────────────────────
    for tool_node in ("sql_node", "rag_node", "web_search_node"):
        graph.add_edge(tool_node, "synthesise_node")

    # ── Linear tail ───────────────────────────────────────────────────────────
    graph.add_edge("synthesise_node",      "update_history_node")
    graph.add_edge("update_history_node",  END)

    return graph.compile()


def save_graph_visualization(compiled_graph, filepath: str = "agent_graph.png") -> None:
    """
    Save the compiled graph as a Mermaid PNG visualization.
    
    Args:
        compiled_graph: The compiled StateGraph from build_graph()
        filepath: Path where to save the PNG file (default: agent_graph.png)
    """
    try:
        graph_obj = compiled_graph.get_graph()
        png_data = graph_obj.draw_mermaid_png()
        with open(filepath, "wb") as f:
            f.write(png_data)
        print(f"Graph visualization saved to {filepath}")
    except Exception as e:
        print(f"Error saving graph visualization: {e}")
