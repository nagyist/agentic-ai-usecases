#!/usr/bin/env python3
"""Visualize the booking graph structure."""

from graph import booking_graph
import os

# Try to generate Mermaid diagram
try:
    # Get the graph visualization in Mermaid format
    mermaid_str = booking_graph.get_graph().draw_mermaid()
    
    print("Mermaid Diagram:")
    print("=" * 60)
    print(mermaid_str)
    print("=" * 60)
    
    # Save to markdown file
    with open("graph_diagram.md", "w") as f:
        f.write("# Flight Booking Assistant Graph\n\n")
        f.write("```mermaid\n")
        f.write(mermaid_str)
        f.write("\n```\n")
    
    print("\n✅ Diagram saved to graph_diagram.md")
    
    # Try to generate PNG using draw_mermaid_png
    try:
        png_data = booking_graph.get_graph().draw_mermaid_png()
        with open("graph_diagram.png", "wb") as f:
            f.write(png_data)
        print("✅ PNG saved to graph_diagram.png")
    except Exception as png_error:
        print(f"⚠️  Could not generate PNG directly: {png_error}")
        print("Trying alternative method...")
        
        # Alternative: try using graphviz if available
        try:
            import subprocess
            # Save Mermaid to file
            with open("temp_diagram.mmd", "w") as f:
                f.write(mermaid_str)
            
            # Try to convert using mmdc (mermaid-cli) if available
            result = subprocess.run(
                ["mmdc", "-i", "temp_diagram.mmd", "-o", "graph_diagram.png"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ PNG saved to graph_diagram.png using mermaid-cli")
            else:
                print(f"⚠️  mermaid-cli not available: {result.stderr}")
        except FileNotFoundError:
            print("⚠️  mermaid-cli (mmdc) not installed")
            print("To install: npm install -g @mermaid-js/mermaid-cli")
    
except Exception as e:
    print(f"Error generating Mermaid diagram: {e}")
    try:
        # Alternative: Try ASCII representation
        print("\nGraph structure:")
        print(booking_graph.get_graph())
    except Exception as e2:
        print(f"Error: {e2}")

# Print graph nodes and edges
print("\n" + "=" * 60)
print("Graph Nodes:")
print("=" * 60)
for node in booking_graph.get_graph().nodes:
    print(f"  - {node}")

print("\n" + "=" * 60)
print("Graph Edges:")
print("=" * 60)
for edge in booking_graph.get_graph().edges:
    print(f"  {edge[0]} -> {edge[1]}")
