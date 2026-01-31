#!/usr/bin/env python3
"""
Visualize the LangGraph booking flow
"""
import os
from dotenv import load_dotenv
from graph import graph

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not set")
    exit(1)

# Get ASCII representation
print("=== LangGraph Booking Flow (ASCII) ===\n")
try:
    ascii_graph = graph.get_graph().draw_ascii()
    print(ascii_graph)
except Exception as e:
    print(f"ASCII visualization failed: {e}")

# Try to get Mermaid diagram
print("\n=== LangGraph Booking Flow (Mermaid) ===\n")
try:
    mermaid = graph.get_graph().draw_mermaid()
    print(mermaid)
    print("\nCopy the above Mermaid diagram to: https://mermaid.live to visualize")
except Exception as e:
    print(f"Mermaid visualization failed: {e}")

# Try PNG visualization (requires graphviz)
print("\n=== LangGraph Booking Flow (PNG) ===\n")
try:
    png_data = graph.get_graph().draw_mermaid_png()
    with open("booking_flow.png", "wb") as f:
        f.write(png_data)
    print("✓ Graph saved to booking_flow.png")
except Exception as e:
    print(f"PNG visualization requires graphviz: {e}")
    print("Install with: brew install graphviz (Mac) or apt-get install graphviz (Linux)")
