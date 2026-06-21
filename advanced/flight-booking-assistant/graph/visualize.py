#!/usr/bin/env python3
"""Visualize the booking graph and its subgraphs.

Run from the project root:
    python -m graph.visualize
"""

import os

from graph import booking_graph
from graph.booking_subgraph import booking_subgraph
from graph.pnr_subgraph import pnr_subgraph

GRAPHS = {
    "top_level":        booking_graph,
    "booking_subgraph": booking_subgraph,
    "pnr_subgraph":     pnr_subgraph,
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def save_graph(name: str, graph, output_dir: str = "."):
    mermaid_str = graph.get_graph().draw_mermaid()

    md_path = f"{output_dir}/{name}.md"
    with open(md_path, "w") as f:
        f.write(f"# {name.replace('_', ' ').title()}\n\n")
        f.write("```mermaid\n")
        f.write(mermaid_str)
        f.write("\n```\n")
    print(f"  Mermaid → {md_path}")

    try:
        png_data = graph.get_graph().draw_mermaid_png()
        png_path = f"{output_dir}/{name}.png"
        with open(png_path, "wb") as f:
            f.write(png_data)
        print(f"  PNG     → {png_path}")
    except Exception as e:
        print(f"  PNG skipped ({e})")


def print_summary(name: str, graph):
    nodes = [n for n in graph.get_graph().nodes if not n.startswith("__")]
    edges = graph.get_graph().edges
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Nodes ({len(nodes)}): {', '.join(nodes)}")
    for src, dst, *_ in edges:
        print(f"  {src} -> {dst}")


if __name__ == "__main__":
    for name, graph in GRAPHS.items():
        print(f"\nProcessing {name}...")
        save_graph(name, graph, output_dir=OUTPUT_DIR)
        print_summary(name, graph)

    print("\nDone.")
