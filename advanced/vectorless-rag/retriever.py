"""
retriever.py
------------
Agent-based retrieval that navigates a DocumentTree to answer a query,
with detailed logging of every LLM call and decision.
"""

import json
import re
import time
import logging
from typing import Annotated, Any, Dict, List, Optional, TypedDict
import operator

from langgraph.graph import StateGraph, END
from openai import OpenAI

from tree import TreeNode, DocumentTree

# ── Logger setup ──────────────────────────────────────────────────────────────
#
# Two handlers:
#   console  — INFO and above, human-readable with colour-coded prefixes
#   file     — DEBUG and above, full detail including raw prompts/responses
#
# Usage from outside:
#   import logging
#   logging.getLogger("retriever").setLevel(logging.DEBUG)  # show raw prompts too

logger = logging.getLogger("retriever")
logger.setLevel(logging.DEBUG)
logger.propagate = False   # don't bubble up to root logger

if not logger.handlers:
    # ── Console handler (INFO) ────────────────────────────────────────────
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _ch.setFormatter(logging.Formatter("%(message)s"))   # raw message only
    logger.addHandler(_ch)

    # ── File handler (DEBUG) ─────────────────────────────────────────────
    _fh = logging.FileHandler("retriever.log", mode="a", encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(_fh)


# ── Visual helpers ────────────────────────────────────────────────────────────

_DIVIDER   = "─" * 65
_SEPARATOR = "═" * 65

def _box(title: str) -> str:
    return f"\n{_SEPARATOR}\n  {title}\n{_SEPARATOR}"

def _indent(text: str, n: int = 4) -> str:
    pad = " " * n
    return "\n".join(pad + line for line in str(text).splitlines())


# ── State ─────────────────────────────────────────────────────────────────────

class RetrievalState(TypedDict):
    query: str
    current_node: Optional[TreeNode]
    tree: TreeNode
    path_taken: Annotated[List[str], operator.add]
    retrieved_content: Annotated[List[str], operator.add]
    reasoning: str
    confidence: float
    should_descend: bool
    target_child_id: Optional[str]
    depth: int
    final_answer: Optional[str]
    call_log: Annotated[List[dict], operator.add]   # full log of every LLM call


# ── Core LLM caller with logging ──────────────────────────────────────────────

def _call_llm(
    client: OpenAI,
    model: str,
    prompt: str,
    call_type: str,          # "navigate" | "answer"
    call_number: int,
) -> tuple[str, float]:
    """
    Call the LLM and log everything:
      - call number and type
      - full prompt (DEBUG / file only)
      - raw response (DEBUG / file only)
      - latency
    Returns (response_text, elapsed_seconds).
    """
    logger.info(f"\n{_DIVIDER}")
    logger.info(f"  LLM Call #{call_number}  [{call_type.upper()}]")
    logger.info(_DIVIDER)

    # Full prompt goes to file (DEBUG) only — too verbose for console
    logger.debug(f"PROMPT:\n{_indent(prompt)}")

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    elapsed = time.perf_counter() - t0
    raw = response.choices[0].message.content.strip()

    logger.debug(f"RAW RESPONSE:\n{_indent(raw)}")
    logger.info(f"  Model    : {model}")
    logger.info(f"  Latency  : {elapsed:.2f}s")
    logger.info(f"  Tokens   : {response.usage.prompt_tokens} in / "
                f"{response.usage.completion_tokens} out")

    return raw, elapsed


def _strip_fences(text: str) -> str:
    if "```" in text:
        for part in text.split("```"):
            part = part.strip().lstrip("json").strip()
            try:
                json.loads(part)
                return part
            except json.JSONDecodeError:
                continue
    return text


# ── Graph nodes ───────────────────────────────────────────────────────────────

def _make_analyze(client: OpenAI, model: str):
    def analyze_node(state: RetrievalState) -> dict:
        # Handle both TreeNode and DocumentTree objects
        if state["current_node"]:
            node: TreeNode = state["current_node"]
        else:
            # If tree is a DocumentTree, get its root; otherwise use it directly
            tree_obj = state["tree"]
            node = tree_obj.root if hasattr(tree_obj, "root") else tree_obj
        
        call_num = len(state["call_log"]) + 1
        depth = state["depth"]

        children_info = (
            [{"id": c.id, "title": c.title,
              "summary": getattr(c, "summary", "")[:150]}
             for c in node.children]
            if node.children else []
        )

        # ── Log: entering this node ───────────────────────────────────────
        logger.info(f"\n{'  ' * depth}┌─ Depth {depth} | Node: \"{node.title}\"")
        logger.info(f"{'  ' * depth}│  id={node.id}  pages={node.page_start}-{node.page_end}")
        logger.info(f"{'  ' * depth}│  children={[c.title for c in node.children] or 'none (leaf)'}")

        prompt = f"""You are navigating a research paper tree to answer a query.

Query: "{state['query']}"

Current node:
  id      : {node.id}
  title   : {node.title}
  summary : {getattr(node, 'summary', '')[:300]}
  pages   : {node.page_start}–{node.page_end}
  preview : {node.content[:500] if node.content else 'N/A'}

Children: {json.dumps(children_info, indent=2) if children_info else "None (leaf node)"}

Decide:
1. confidence      : 0–1, how likely does this node (or its children) contain the answer?
2. should_descend  : true only if a specific child is more relevant than this node's content
3. target_child_id : the id of the best child to visit (null if should_descend is false)
4. reasoning       : one sentence explaining your decision

Respond ONLY as valid JSON, no markdown fences:
{{
  "confidence": 0.85,
  "should_descend": true,
  "target_child_id": "1_Introduction_12",
  "reasoning": "The Introduction section directly addresses what Bigtable is."
}}"""

        raw, elapsed = _call_llm(client, model, prompt, "navigate", call_num)
        raw = _strip_fences(raw)

        try:
            decision = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"  [!] JSON parse failed — using fallback decision")
            decision = {
                "confidence": 0.5,
                "should_descend": bool(node.children),
                "target_child_id": node.children[0].id if node.children else None,
                "reasoning": "Fallback: could not parse LLM response",
            }

        conf      = float(decision.get("confidence", 0.5))
        descend   = bool(decision.get("should_descend", False))
        child_id  = decision.get("target_child_id")
        reasoning = decision.get("reasoning", "")

        # ── Log: decision ─────────────────────────────────────────────────
        arrow = "↓ descend" if (descend and node.children) else "→ retrieve"
        logger.info(f"{'  ' * depth}│")
        logger.info(f"{'  ' * depth}│  Decision   : {arrow}")
        logger.info(f"{'  ' * depth}│  Confidence : {conf:.0%}")
        if child_id and descend:
            logger.info(f"{'  ' * depth}│  Next node  : {child_id}")
        logger.info(f"{'  ' * depth}│  Reasoning  : {reasoning}")
        logger.info(f"{'  ' * depth}└─ ({elapsed:.2f}s)")

        entry = {
            "call_number":    call_num,
            "call_type":      "navigate",
            "node_id":        node.id,
            "node_title":     node.title,
            "depth":          depth,
            "confidence":     conf,
            "should_descend": descend,
            "target_child":   child_id,
            "reasoning":      reasoning,
            "latency_s":      round(elapsed, 3),
        }

        return {
            "path_taken":      [node.id],     # LangGraph appends automatically
            "current_node":    node,
            "confidence":      conf,
            "should_descend":  descend,
            "target_child_id": child_id,
            "reasoning":       reasoning,
            "depth":           depth + 1,
            "call_log":        [entry],        # LangGraph appends automatically
        }

    return analyze_node


def _make_descend():
    def descend(state: RetrievalState) -> dict:
        current: TreeNode = state["current_node"]
        target_id: Optional[str] = state.get("target_child_id")
        depth = state["depth"]

        target = next(
            (c for c in current.children if c.id == target_id),
            current.children[0],
        )

        logger.info(f"\n{'  ' * depth}➜  Descending into: \"{target.title}\"")

        return {"current_node": target}

    return descend


def _make_retrieve():
    def retrieve(state: RetrievalState) -> dict:
        node: TreeNode = state["current_node"]
        depth = state["depth"]

        logger.info(f"\n{'  ' * depth}✦  Retrieving content from: \"{node.title}\"")
        logger.info(f"{'  ' * depth}   Pages {node.page_start}–{node.page_end} | "
                    f"{len(node.content)} chars")

        chunk = (
            f"=== **{node.title}** "
            f"(Pages {node.page_start}-{node.page_end}) ===\n"
            f"{node.content}"
        )
        return {"retrieved_content": [chunk]}   # LangGraph appends automatically

    return retrieve


def _make_generate(client: OpenAI, model: str):
    def generate_answer(state: RetrievalState) -> dict:
        call_num  = len(state["call_log"]) + 1
        context   = "\n\n---\n\n".join(state["retrieved_content"])
        sources   = [s.splitlines()[0] for s in state["retrieved_content"]]

        logger.info(f"\n{_DIVIDER}")
        logger.info(f"  Generating answer from {len(state['retrieved_content'])} "
                    f"retrieved section(s):")
        for s in sources:
            logger.info(f"    • {s}")

        prompt = f"""You are an expert on distributed systems and database engineering.
Answer the question using ONLY the retrieved document sections below.
Cite the section title and page range for every claim you make.
If the context is insufficient, say so clearly — do not guess.

Question: {state['query']}

Retrieved sections:
{context}

Answer:"""

        raw, elapsed = _call_llm(client, model, prompt, "answer", call_num)

        entry = {
            "call_number": call_num,
            "call_type":   "answer",
            "sources":     sources,
            "latency_s":   round(elapsed, 3),
        }

        logger.info(f"\n  Answer generated in {elapsed:.2f}s")

        return {
            "final_answer": raw,
            "call_log":     [entry],
        }

    return generate_answer


# ── Routing ───────────────────────────────────────────────────────────────────

MAX_DEPTH = 5

def _route(state: RetrievalState) -> str:
    if state["confidence"] < 0.3:
        logger.info(f"\n  ✗  Low confidence ({state['confidence']:.0%}) — stopping traversal")
        return "end"
    if state["depth"] >= MAX_DEPTH:
        logger.info(f"\n  ⚠  Max depth ({MAX_DEPTH}) reached — retrieving current node")
        return "retrieve"
    if state["should_descend"] and state["current_node"].children:
        return "descend"
    return "retrieve"


# ── Graph assembly ────────────────────────────────────────────────────────────

def _build_graph(client: OpenAI, model: str) -> Any:
    workflow = StateGraph(RetrievalState)

    workflow.add_node("analyze",  _make_analyze(client, model))
    workflow.add_node("descend",  _make_descend())
    workflow.add_node("retrieve", _make_retrieve())
    workflow.add_node("generate", _make_generate(client, model))

    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges(
        "analyze", _route,
        {"descend": "descend", "retrieve": "retrieve", "end": END},
    )
    workflow.add_edge("descend",  "analyze")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# ── Visualization ─────────────────────────────────────────────────────────────

def generate_workflow_png(output_path: str = "workflow.png") -> str:
    """
    Generate a PNG visualization of the LangGraph workflow structure.

    Args:
        output_path: Path where the PNG will be saved (default: "workflow.png")

    Returns:
        Path to the generated PNG file
    """
    workflow = StateGraph(RetrievalState)
    
    # Add nodes (dummy functions for structure visualization)
    workflow.add_node("analyze",  lambda state: state)
    workflow.add_node("descend",  lambda state: state)
    workflow.add_node("retrieve", lambda state: state)
    workflow.add_node("generate", lambda state: state)
    
    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges(
        "analyze", lambda state: "retrieve",
        {"descend": "descend", "retrieve": "retrieve", "end": END},
    )
    workflow.add_edge("descend",  "analyze")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    graph = workflow.compile()
    graph_image = graph.get_graph().draw_mermaid_png()
    
    with open(output_path, "wb") as f:
        f.write(graph_image)
    
    logger.info(f"Workflow visualization saved to: {output_path}")
    return output_path


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(query: str, tree: TreeNode, client: OpenAI, model: str = "gpt-4o-mini") -> Dict:
    """
    Navigate the document tree and answer a query, logging every LLM call.

    Console output (INFO):
        Shows the traversal path, each decision, confidence, and reasoning.

    File output (DEBUG → retriever.log):
        Additionally logs the full prompt and raw LLM response for every call.
    """
    logger.info(_box(f"New Query"))
    logger.info(f"\n  Q: {query}\n")

    graph = _build_graph(client, model)

    t_start = time.perf_counter()

    result = graph.invoke({
        "query":             query,
        "current_node":      None,
        "tree":              tree,
        "path_taken":        [],
        "retrieved_content": [],
        "reasoning":         "",
        "confidence":        0.0,
        "should_descend":    True,
        "target_child_id":   None,
        "depth":             0,
        "final_answer":      None,
        "call_log":          [],
    })

    total_s = time.perf_counter() - t_start
    call_log = result.get("call_log", [])
    nav_calls = sum(1 for c in call_log if c["call_type"] == "navigate")
    ans_calls = sum(1 for c in call_log if c["call_type"] == "answer")

    # ── Final summary ──────────────────────────────────────────────────────
    logger.info(f"\n{_SEPARATOR}")
    logger.info("  RETRIEVAL SUMMARY")
    logger.info(_SEPARATOR)
    logger.info(f"  Total LLM calls : {len(call_log)}  "
                f"({nav_calls} navigate + {ans_calls} answer)")
    logger.info(f"  Path taken      : {' → '.join(result.get('path_taken', []))}")
    logger.info(f"  Total latency   : {total_s:.2f}s")
    logger.info(_SEPARATOR)

    return {
        "answer":     result.get("final_answer") or "No answer generated (low confidence).",
        "path":       result.get("path_taken", []),
        "reasoning":  result.get("reasoning", ""),
        "confidence": result.get("confidence", 0.0),
        "sources":    result.get("retrieved_content", []),
        "call_log":   call_log,
    }