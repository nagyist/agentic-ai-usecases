"""
main.py
-------
Vectorless RAG — LangGraph Agent + PDF Tree (no PageIndex)

Flow:
  1. Download Bigtable PDF
  2. Parse PDF → DocumentTree  (one-time, cached to JSON)
  3. For each question: agent traverses the tree → retrieves sections → generates answer

Install:
  pip install PyMuPDF openai langgraph pydantic python-dotenv

.env:
  OPENAI_API_KEY=sk-...
"""

import json
import os
import urllib.request
from pathlib import Path
from dataclasses import asdict

from dotenv import load_dotenv
from openai import OpenAI

from questions import QUESTIONS
from retriever import retrieve, generate_workflow_png
from tree import parse_pdf, TreeNode

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
PDF_URL = (
    "https://static.googleusercontent.com/media/research.google.com"
    "/en//archive/bigtable-osdi06.pdf"
)
PDF_PATH        = Path("bigtable-osdi06.pdf")
TREE_CACHE_PATH = Path("results/document_tree.json")
MODEL           = "gpt-4o-mini"

# ── Init client (one instance, shared across tree.py and retriever.py) ────────
if not os.environ.get("OPENAI_API_KEY"):
    raise SystemExit(
        "OPENAI_API_KEY not set.\n"
        "Create a .env file with:  OPENAI_API_KEY=sk-..."
    )

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ── Step 1: Download PDF ──────────────────────────────────────────────────────
def download_pdf() -> None:
    if PDF_PATH.exists():
        print(f"[✓] PDF already present: {PDF_PATH}")
        return
    print("[↓] Downloading Bigtable paper …")
    urllib.request.urlretrieve(PDF_URL, PDF_PATH)
    print(f"[✓] Saved → {PDF_PATH}")


# ── Step 2: Build / load tree ─────────────────────────────────────────────────
def dict_to_treenode(data: dict) -> TreeNode:
    """Recursively reconstruct TreeNode from dictionary."""
    children = [
        dict_to_treenode(child) for child in data.get("children", [])
    ]
    data_copy = data.copy()
    data_copy["children"] = children
    return TreeNode(**data_copy)


def get_tree() -> TreeNode:
    """
    Load cached TreeNode from JSON, or build and cache it fresh.
    """
    TREE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if TREE_CACHE_PATH.exists():
        print(f"[✓] Loading cached tree from {TREE_CACHE_PATH}")
        with open(TREE_CACHE_PATH) as f:
            data = json.load(f)
        # Reconstruct TreeNode from cached dict (extract root from DocumentTree)
        tree = dict_to_treenode(data.get("root", data))
        print(f"    {len(tree.children)} sections loaded")
        return tree

    print("[~] Building tree (first run — takes ~10–30 sec with PyMuPDF4LLM) …")
    tree = parse_pdf(str(PDF_PATH))

    with open(TREE_CACHE_PATH, "w") as f:
        json.dump(asdict(tree), f, indent=2, default=str)
    print(f"[✓] Tree cached → {TREE_CACHE_PATH}")
    return tree


# ── Step 3: Ask a question ────────────────────────────────────────────────────
def ask(question: str, tree: TreeNode) -> dict:
    print(f"\n{'─'*70}")
    print(f"  Q: {question}")
    print(f"{'─'*70}")

    # Pass the LLM client to retrieve function
    result = retrieve(question, tree, client)

    print(f"\n  [Reasoning]  {result['reasoning']}")
    print(f"  [Confidence] {result['confidence']:.0%}")
    print(f"  [Path]       {' → '.join(result['path'])}")

    if result["sources"]:
        print(f"\n  [Sources]")
        for src in result["sources"][:2]:
            print(f"    {src.splitlines()[0]}")   # just the header line

    print(f"\n  [Answer]\n{result['answer']}")
    return result


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    download_pdf()
    
    # Load or build the tree
    tree = get_tree()    
    # Generate workflow visualization
    TREE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    workflow_png_path = TREE_CACHE_PATH.parent / "workflow.png"
    generate_workflow_png(output_path=str(workflow_png_path))
    print(f"[✓] Workflow diagram saved → {workflow_png_path}")
    print(f"\n{'═'*70}")
    print("  Vectorless RAG — Google Bigtable (no PageIndex)")
    print(f"{'═'*70}")

    results = []
    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}]")
        try:
            result = ask(question, tree)
            results.append({"question": question, "result": result, "ok": True})
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({"question": question, "error": str(e), "ok": False})

    ok = sum(r["ok"] for r in results)
    print(f"\n{'═'*70}")
    print(f"  Done: {ok}/{len(results)} questions answered successfully")
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    main()