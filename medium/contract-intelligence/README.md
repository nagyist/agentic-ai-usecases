# Contract Intelligence System

An AI-powered pipeline that extracts key commercial terms from contract documents (PDF, images, XML) using PaddleOCR, Hybrid RAG (FAISS + BM25), and GPT-4o — with results exported to a structured Excel report.

---

## Overview

Contracts contain business-critical information — supplier names, dates, payment terms, rate cards — buried in unstructured documents. This system automates extraction into a structured format using a 5-stage LangGraph pipeline.

**Supported formats:** PDF (multi-page) · JPG · PNG · TIFF · XML

**Extracted fields:**
| Field | Description |
|---|---|
| Party A Legal Name | First contracting party |
| Party B Legal Name | Second contracting party |
| Start Date | Contract commencement date |
| End Date | Contract expiry / termination date |
| Price Details (Rate Card) | Itemised pricing table |
| Payment Timeline | When payments are due (Net 30, Net 60, etc.) |
| Payment Conditions | Conditions governing payment release |

---

## Architecture

```
Upload (PDF / Image / XML)
         │
         ▼
┌─────────────────────┐
│  1. Pre-processing  │  PDF → page images via PyMuPDF; image dedup (imagehash)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  2. OCR Extraction  │  PaddleOCR per page → raw text by page
└────────┬────────────┘       (cached to Excel; skippable on re-runs)
         │
         ▼
┌──────────────────────────┐
│  3. Indexing             │  Text → chunks (600 chars, 100 overlap)
│  FAISS (semantic)        │  sentence-transformers/all-MiniLM-L6-v2
│  BM25  (keyword)         │  rank-bm25
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  4. Field Extraction     │  Per-field RAG queries → RRF fusion → GPT-4o-mini
│  (LangGraph Agent)       │  Returns value + confidence score + page reference
└────────┬─────────────────┘
         │
         ▼
┌─────────────────────┐
│  5. Excel Export    │  3-sheet workbook: Fields · Rate Card · Raw OCR
└─────────────────────┘
```

### LangGraph Pipeline

```python
preprocess → ocr_extract → index → extract → generate_excel → END
```

Each node is a pure function that transforms a shared `ContractState` TypedDict.

---

## Project Structure

```
contract-intelligence/
├── app.py                    # Streamlit UI entry point
├── graph.py                  # LangGraph StateGraph definition
├── graph_workflow.png        # Auto-generated pipeline diagram
├── requirements.txt
├── config/
│   └── settings.py           # API keys, model names, chunk sizes, confidence thresholds
├── models/
│   └── state.py              # ContractState TypedDict
├── nodes/
│   ├── preprocessing.py      # PDF → page images, deduplication
│   ├── ocr_extraction.py     # PaddleOCR per-page text extraction
│   ├── indexing.py           # FAISS + BM25 index construction
│   ├── extraction_agent.py   # Per-field RAG + GPT-4o extraction
│   ├── excel_generation.py   # openpyxl workbook generation
│   └── validation_agent.py   # Post-extraction validation
├── services/
│   ├── embeddings.py         # sentence-transformers wrapper
│   ├── llm.py                # OpenAI client wrapper
│   └── vector_store.py       # FAISS index operations
├── utils/
│   ├── file_utils.py         # File type detection
│   ├── ocr_cache.py          # OCR result caching / loading from Excel
│   └── progress.py           # Thread-safe progress queue for UI
└── data/
    ├── temp/                 # Temporary files during processing
    └── output/               # Generated Excel reports
```

---

## Setup

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation

```bash
cd medium/contract-intelligence
pip install paddlepaddle          # CPU version (required before paddleocr)
pip install -r requirements.txt
```

> **Note:** PaddleOCR downloads model weights (~500 MB) on first run. Subsequent runs are fast.

### Environment Variables

Create a `.env` file at the **repository root** (or export variables directly):

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini          # optional, defaults to gpt-4o-mini
```

---

## Running the App

```bash
cd medium/contract-intelligence
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Usage

1. **Upload** a contract file (PDF, JPG, PNG, TIFF, or XML).
2. **OCR Cache** — if a previous run's Excel exists for the same file, a toggle lets you skip the OCR step (~5–10 min) and reuse cached text.
3. Click **🚀 Process Contract** to run the 5-stage pipeline.
4. View results across 5 tabs:
   - **📋 Extracted Fields** — values with confidence badges (🟢 / 🟡 / 🔴) and source snippets
   - **💰 Rate Card** — price detail table
   - **📄 Raw OCR Text** — per-page extracted text
   - **🔍 Prompt Log** — full RAG queries, retrieved chunks, prompts, and token usage
   - **🗒️ Processing Log** — step-by-step execution trace
5. **📥 Download Full Excel Report** — 3-sheet workbook with all results.

---

## Tech Stack

| Component | Library / Model |
|---|---|
| UI | Streamlit ≥ 1.36 |
| Workflow | LangGraph ≥ 0.2 |
| OCR | PaddleOCR ≥ 2.7.3 + OpenCV |
| PDF rendering | PyMuPDF ≥ 1.24 |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Vector search | FAISS (faiss-cpu ≥ 1.8) |
| Keyword search | rank-bm25 ≥ 0.2.2 |
| Fusion | Reciprocal Rank Fusion (RRF) |
| LLM | OpenAI GPT-4o-mini |
| Excel output | openpyxl ≥ 3.1 |

---

## Key Design Decisions

- **Hybrid RAG (FAISS + BM25 → RRF):** Semantic search alone misses exact terms (e.g. "Net 30"). BM25 captures keyword matches; RRF fuses rankings without tuning weights.
- **Parent-document retrieval:** Child chunks (600 chars) are ranked for precision, but the full page text is passed to the LLM for context.
- **Per-field extraction:** Each field gets its own targeted RAG queries, rather than one giant prompt over the full document. This improves accuracy and makes token usage traceable.
- **OCR caching:** PaddleOCR is slow on CPU (~5–10 min for a 20-page PDF). Caching raw text to the output Excel lets you re-run field extraction without repeating OCR.
- **Confidence scoring:** Every extracted field carries a 0–1 confidence score. Results below 50% are flagged red; 50–80% yellow; 80%+ green.

---

## Article

[Build an AI Contract Intelligence System: OCR + Hybrid RAG + LangGraph to Extract Key Terms Automatically](https://medium.com/@alphaiterations)
