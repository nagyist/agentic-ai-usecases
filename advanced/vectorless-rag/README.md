# Vectorless RAG: A Reasoning-Based Document Retrieval System

> **Retrieval without vectors. Reasoning without embeddings. Just pure LLM intelligence.**
>
> [Read Medium Article here](https://medium.com/towards-artificial-intelligence/vectorless-rag-how-i-built-a-rag-system-without-embeddings-databases-or-vector-similarity-efccf21e42ff)

## Overview

This repository demonstrates **Vectorless RAG** (Retrieval-Augmented Generation) — a novel approach to document question-answering that replaces traditional vector databases with **intelligent tree-based document structure** and **LLM reasoning**.

Unlike conventional RAG systems that use:
- ❌ Vector embeddings (high cost, slow, semantic drift)
- ❌ Fixed-size chunks (lose context, artificial boundaries)
- ❌ Similarity search (relevance ≠ similarity)

This system uses:
- ✅ **Hierarchical document tree** (like a table of contents)
- ✅ **LLM reasoning** (understanding, not matching)
- ✅ **Context awareness** (maintains document structure)
- ✅ **Full citation** (traceable results with page numbers)

---

## 🎯 Quick Start

### Setup

#### 1. Create and Activate Virtual Environment

**For macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**For Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**For Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Configure API Key
Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your-api-key-here
```

#### 4. Run the System
```bash
python main.py
```

### What Happens

1. **Downloads** the Google Bigtable paper (one-time)
2. **Checks** for cached tree at `results/document_tree.json`
3. **Builds** the tree (only if cache doesn't exist, ~1–2 minutes)
4. **Generates** a workflow visualization PNG to `results/workflow.png`
5. **Asks** sample questions using vectorless RAG
6. **Returns** cited answers with page numbers

---

## 🏗️ System Architecture

The system uses a **graph-based agent** (LangGraph) that intelligently navigates the document tree through four main stages:

1. **Analyze Node**: LLM evaluates relevance of current section and decides navigation strategy
2. **Route Decision**: Based on confidence score, either descend into children, retrieve content, or backtrack
3. **Retrieve Content**: Extract full text from relevant document sections
4. **Generate Answer**: LLM synthesizes final answer with sources and citations

A **workflow visualization PNG** is automatically generated and saved to `results/workflow.png` showing the complete agent state graph structure.

The document tree itself is built using a **5-stage pipeline** that progressively refines document structure detection, starting with no LLM calls and only using AI where necessary for complex hierarchies.

---

## 📊 Core Concepts

### TreeNode Structure

A **TreeNode** is a hierarchical representation of document sections that preserves the full document structure. Each node contains:

- **id**: Unique identifier for tracking retrieval path
- **title**: Section heading from document
- **summary**: AI-generated summary for relevance evaluation
- **page_start/page_end**: Page range for citations
- **content**: Full text of the section
- **children**: Nested TreeNode list (preserves document structure)
- **level**: Hierarchy depth (0=root, 1=section, 2=subsection, etc.)

### Agent-Based Retrieval

The **LangGraph-based agent** navigates the document tree using an annotated typed dictionary (RetrievalState) that tracks:

- Current query and navigation position
- Full document tree and traversal path
- Retrieved content blocks and reasoning
- Confidence score (0.0-1.0) for relevance decisions
- Generated final answer

The agent makes intelligent routing decisions:
- **Analyze**: Evaluate section relevance to query
- **Decide**: Route to child sections (descend), extract content (retrieve), or backtrack
- **Retrieve**: Extract full text from selected sections
- **Generate**: Synthesize final answer from all retrieved content

### How Hierarchy Improves Retrieval

Natural document structure enables intelligent navigation without embeddings:

- **Preservation**: Natural sections maintain multi-sentence context
- **Navigation**: Hierarchy allows topic-specific drilling instead of keyword matching
- **Reasoning**: LLM understands document organization
- **Citations**: Every answer traces back to specific pages and sections

---

## �️ API Reference

### Building the Document Tree

The `parse_pdf()` function from `tree.py` creates a DocumentTree with automatic structure detection:

- Supports optional page limit for testing
- Tree contains document metadata (name, total pages) and hierarchical root node
- Caching is handled separately via JSON serialization

### Retrieving Answers

The `retrieve()` function from `retriever.py` runs the agent-based retrieval pipeline:

- Returns a result dictionary with answer, traversal path, reasoning, confidence score, and sources
- Handles multi-hop reasoning across document sections
- Provides citations and page ranges for all retrieved content

### Generating Workflow Visualization

The `generate_workflow_png()` function from `retriever.py` creates a PNG visualization:

- Visualizes the complete LangGraph state machine
- Shows all nodes and conditional routing logic
- Saves to specified output path (default: "workflow.png")
- Automatically called by `main.py` and saved to `results/workflow.png`

### Tree Caching

DocumentTree objects can be serialized to JSON and cached for reuse:

- Load from cache if available to skip expensive tree building
- Save tree after first build using `model_dump()` method
- Significantly speeds up repeated queries on the same document

---

## 🔄 Complete Agent Walkthrough

### Example Question: "What is Bigtable and what problem does it solve?"

**Initial State:**
The agent starts at the document root with no current position established.

**Step 1: Analyze Node (at Root)**
The agent evaluates the root node's relevance and determines whether to descend into child sections (like Introduction, Architecture, etc.) or immediately retrieve content.

**Step 2: Route Decision**
Based on confidence score (threshold: 0.3), the agent either descends deeper into relevant child sections or moves to content retrieval.

**Step 3: Navigation**
The agent traverses through the document hierarchy, analyzing each section's relevance until finding high-confidence content.

**Step 4: Retrieve Content**
Once a relevant section is found, the agent extracts the full text content for that node.

**Step 5: Generate Answer**
The final LLM call synthesizes the retrieved content into a comprehensive answer with citations and source tracking.

---

---

## 🛠️ Running Sample Questions

Edit the `QUESTIONS` list in `questions.py` to customize which questions the system answers. The questions will be processed sequentially using the vectorless RAG pipeline.

---

## 📈 Key Advantages vs Vector RAG

| Aspect | Vector RAG | Vectorless RAG |
|--------|-----------|----------------|
| **Chunking** | Fixed 512-token chunks (lose context) | Natural sections (preserve structure) |
| **Embeddings** | Must embed every chunk (expensive) | None (just tree structure) |
| **Search Quality** | Similarity matching (can miss relevance) | LLM reasoning (understands context) |
| **Citations** | Vague chunk IDs | Page ranges and section titles |
| **Multi-hop** | Often fails without re-ranking | Naturally handles multi-section concepts |
| **Hallucination** | Higher (semantic drift from chunks) | Lower (grounded in full sections) |
| **Cost** | Ongoing embedding costs | One-time tree building |

---

## ⚙️ Configuration

### Environment Setup

Create a `.env` file in the project root with your OpenAI API key. Install dependencies using `pip install -r requirements.txt`.

### Tree Building Configuration

The `parse_pdf()` function supports customization:

- **Custom models**: Use lower-cost models like gpt-3.5-turbo or gpt-4o-mini
- **Page limits**: Specify `k` parameter to limit to first k pages (useful for testing)
- **Full document processing**: Default mode analyzes entire PDF

---

## 🔍 Debugging & Troubleshooting

### Inspect TreeNode Structure

The document tree can be inspected by walking the hierarchy and examining node properties. Print the tree structure to understand how the PDF was parsed into sections and subsections.

---

## 📚 Architecture Deep Dive

### Tree Construction Pipeline

The document tree is built using a **5-stage pipeline** that progressively refines document structure:

1. **PyMuPDF Embedded TOC** — Reads PDF's native bookmark structure (0 LLM calls)
2. **Regex Heading Scan** — Scans for numbered headings like "2.3 Column Families" (0 LLM calls)
3. **Font-Based Scan** — Analyzes font metrics to identify heading fonts (0 LLM calls)
4. **LLM Structure Detection** — Used when regex finds few sections, analyzes text flow (1 LLM call)
5. **Per-Section Summaries** — Generates 2-sentence summaries for each section (N small calls)

Multiple detection methods are merged intelligently based on confidence in the regex results.

### Agent-Based Retrieval (LangGraph)

The retrieval agent uses a **StateGraph** with the following structure:

**State Variables:**
- `query`: User question
- `current_node`: Current position in tree
- `tree`: Full document hierarchy
- `path_taken`: Visited node IDs
- `retrieved_content`: Content blocks accumulated
- `reasoning`: LLM explanation
- `confidence`: Relevance score (0.0-1.0)
- `should_descend`: Navigation decision
- `final_answer`: Generated response

**Graph Nodes:**
- analyze: Evaluate current node relevance
- descend: Move to child node
- retrieve: Extract node content
- generate: Synthesize final answer

**Conditional Routing:**
- If confidence > 0.3 and children exist → descend
- If confidence ≤ 0.3 or no children → retrieve
- If maximum depth reached → backtrack

---

## 📖 Further Reading

- **PageIndex Framework:** https://github.com/VectifyAI/PageIndex
- **Blog Post:** https://pageindex.ai/blog/pageindex-intro
- **Research Paper:** https://vectify.ai/blog/Mafin2.5
- **API Documentation:** https://pageindex.ai/developer

---

## License

This implementation is part of the agentic-ai-usecases repository. See LICENSE for details.


**Happy reasoning! 🚀**
