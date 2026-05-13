import csv
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

from models.state import ContractState
from services.llm import LLMService
from services.vector_store import HybridVectorStore
from config.settings import EXTRACT_FIELDS, TOP_K_RETRIEVAL, OUTPUT_DIR, FIELD_DISPLAY_NAMES

# ── Per-field search queries (multiple angles for better recall) ──────────────

FIELD_QUERIES: Dict[str, List[str]] = {
    "supplier_legal_name": [
        "supplier legal name vendor company name",
        "party providing services seller name",
        "service provider corporation registered name",
    ],
    "receiver_legal_entity": [
        "buyer client purchaser legal entity name",
        "customer company receiving party",
        "client corporation receiver official name",
    ],
    "start_date": [
        "contract start date commencement effective date",
        "agreement begins from date contract period start",
        "effective from date of contract",
    ],
    "end_date": [
        "contract end date expiry termination date",
        "agreement expires valid until contract period end",
        "contract completion date",
    ],
    "price_details": [
        "rate card price list pricing table fees charges",
        "unit price amount cost per item service rate",
        "pricing schedule tariff commercial rates",
        "fee structure price per unit volume pricing",
    ],
    "payment_term": [
        "payment terms net days due invoice payment conditions",
        "payment schedule net 30 net 60 days due",
        "invoice settlement period payment deadline",
    ],
    "price_validity_period": [
        "price validity period pricing freeze valid until",
        "prices valid for rate lock period pricing effective",
        "price validity end date commercial terms freeze",
    ],
}

# ── Per-field extraction prompts ──────────────────────────────────────────────

FIELD_PROMPTS: Dict[str, str] = {
    "supplier_legal_name": (
        "Extract the full official legal name of the Supplier / Vendor / Service Provider "
        "from this contract. Look for labels like 'Supplier:', 'Vendor:', 'Service Provider:', "
        "'Party A:', 'Seller:' or company registration names near signature blocks."
    ),
    "receiver_legal_entity": (
        "Extract the full official legal name of the Buyer / Client / Customer / Receiver "
        "from this contract. Look for 'Buyer:', 'Client:', 'Customer:', 'Party B:', "
        "'Purchaser:', 'Receiver:'."
    ),
    "start_date": (
        "Extract the contract start / commencement / effective date. "
        "Look for 'Start Date:', 'Effective Date:', 'Commencement Date:', 'From:', "
        "'Contract Period begins:'. Normalise to YYYY-MM-DD if possible."
    ),
    "end_date": (
        "Extract the contract end / expiry / termination date. "
        "Look for 'End Date:', 'Expiry Date:', 'Termination Date:', 'Valid Until:', "
        "'Contract Period ends:'. Normalise to YYYY-MM-DD if possible."
    ),
    "price_details": (
        "Extract the complete rate card / pricing table from this contract. "
        "This may include service items, product SKUs, unit prices, currencies, volume tiers, "
        "or any other commercial pricing information. The schema is dynamic – capture every "
        "column and row as found in the document."
    ),
    "payment_term": (
        "Extract the payment terms. Look for net payment days (e.g. 'Net 30', 'Net 60'), "
        "payment schedules, due dates, early payment discounts, and late payment penalties."
    ),
    "price_validity_period": (
        "Extract the price validity period / price freeze window. "
        "Look for 'Prices valid until:', 'Price Validity:', 'Rate Lock Period:', "
        "'Pricing Freeze:', 'Price Validity Period:'."
    ),
}


# ── Retrieval stats dataclass (plain dict for simplicity) ─────────────────────

def _empty_stats(field: str) -> Dict[str, Any]:
    return {"field": field, "chunks_retrieved": 0, "pages_passed": 0, "page_numbers": []}


# ── Retrieval ─────────────────────────────────────────────────────────────────

def _retrieve_top_chunks(field: str, store: HybridVectorStore) -> List[Dict]:
    """Multi-query retrieval with deduplication, returns top-k child chunks."""
    seen: set = set()
    results: List[Dict] = []
    for q in FIELD_QUERIES[field]:
        for r in store.hybrid_search(q, k=4):
            key = r["chunk"][:80]
            if key not in seen:
                seen.add(key)
                results.append(r)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:TOP_K_RETRIEVAL]


def _build_parent_context(chunks: List[Dict]) -> Tuple[str, List[int]]:
    """Expand child chunks to their full parent pages (deduplicated).

    Returns the context string and the sorted list of unique page numbers (1-indexed).
    """
    seen_pages: Dict[int, str] = {}
    for r in chunks:
        pg = r["metadata"].get("page", 0)
        if pg not in seen_pages:
            seen_pages[pg] = r["metadata"].get("page_text") or r["chunk"]

    context = "\n\n".join(
        f"[Full page {pg + 1}]\n{text}"
        for pg, text in sorted(seen_pages.items())
    )
    page_numbers = sorted(pg + 1 for pg in seen_pages)
    return context, page_numbers


# ── Extraction ────────────────────────────────────────────────────────────────

def _extract_field(
    field: str,
    store: HybridVectorStore,
    llm: LLMService,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Returns (extraction result, retrieval stats)."""
    top_chunks = _retrieve_top_chunks(field, store)
    context, page_numbers = _build_parent_context(top_chunks)

    stats = {
        "field": field,
        "chunks_retrieved": len(top_chunks),
        "pages_passed": len(page_numbers),
        "page_numbers": page_numbers,
    }

    if field == "price_details":
        prompt = f"""{FIELD_PROMPTS[field]}

Contract pages:
{context}

Return JSON:
{{
  "value": [
    {{"item": "...", "unit": "...", "price": "...", "currency": "...", "notes": "..."}}
  ],
  "confidence": <0.0–1.0>,
  "page_ref": <page number or null>,
  "raw_text": "<short verbatim snippet>"
}}

The "value" array must contain ALL pricing rows found. Add or remove keys dynamically
to match what is actually in the document (e.g. add "tier", "discount", "validity" etc.).
If no price data is found: {{"value": [], "confidence": 0.0, "page_ref": null, "raw_text": ""}}"""
    else:
        prompt = f"""{FIELD_PROMPTS[field]}

Contract pages:
{context}

Return JSON:
{{
  "value": "<extracted value or null>",
  "confidence": <0.0–1.0>,
  "page_ref": <page number or null>,
  "raw_text": "<short verbatim snippet>"
}}

If not found: {{"value": null, "confidence": 0.0, "page_ref": null, "raw_text": ""}}"""

    response = llm.generate_json(prompt)

    if not response or "value" not in response:
        return {"value": None, "confidence": 0.0, "page_ref": None, "raw_text": ""}, stats

    if response.get("page_ref") is None and top_chunks:
        response["page_ref"] = top_chunks[0]["metadata"].get("page", 0) + 1

    return response, stats


# ── Retrieval log helpers ─────────────────────────────────────────────────────

_CSV_HEADER = ["timestamp", "document", "field", "display_name",
               "chunks_retrieved", "pages_passed", "page_numbers"]


def _print_retrieval_table(all_stats: List[Dict[str, Any]], document: str) -> None:
    col = "{:<28} {:>16} {:>12} {}"
    header = col.format("Field", "Chunks Retrieved", "Pages Passed", "Page Numbers")
    divider = "-" * len(header)
    print(f"\n{'='*60}")
    print(f"  Retrieval log — {document}")
    print(f"{'='*60}")
    print(header)
    print(divider)
    for s in all_stats:
        pages_str = str(s["page_numbers"]) if s["page_numbers"] else "[]"
        print(col.format(
            FIELD_DISPLAY_NAMES.get(s["field"], s["field"]),
            s["chunks_retrieved"],
            s["pages_passed"],
            pages_str,
        ))
    print(f"{'='*60}\n")


def _write_csv(all_stats: List[Dict[str, Any]], document: str) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = Path(OUTPUT_DIR) / f"retrieval_log_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_HEADER)
        writer.writeheader()
        for s in all_stats:
            writer.writerow({
                "timestamp": ts,
                "document": document,
                "field": s["field"],
                "display_name": FIELD_DISPLAY_NAMES.get(s["field"], s["field"]),
                "chunks_retrieved": s["chunks_retrieved"],
                "pages_passed": s["pages_passed"],
                "page_numbers": ";".join(str(p) for p in s["page_numbers"]),
            })
    return csv_path


# ── Node ─────────────────────────────────────────────────────────────────────

def extraction_agent_node(state: ContractState) -> dict:
    from nodes.indexing import get_session_store  # avoids circular import at module level

    log = list(state.get("processing_log", []))
    store = get_session_store()
    llm = LLMService()
    extracted: Dict[str, Any] = {}
    all_stats: List[Dict[str, Any]] = []
    document = state.get("original_filename", "contract")

    for field in EXTRACT_FIELDS:
        try:
            result, stats = _extract_field(field, store, llm)
            extracted[field] = result
            all_stats.append(stats)
        except Exception as e:
            extracted[field] = {
                "value": None,
                "confidence": 0.0,
                "page_ref": None,
                "raw_text": "",
                "error": str(e),
            }
            all_stats.append(_empty_stats(field))

    _print_retrieval_table(all_stats, document)
    csv_path = _write_csv(all_stats, document)

    found = sum(1 for v in extracted.values() if v.get("value"))
    log.append(f"Extraction complete: {found}/{len(EXTRACT_FIELDS)} fields found")
    log.append(f"Retrieval log saved: {csv_path}")

    return {
        **state,
        "extracted_fields": extracted,
        "processing_log": log,
        "current_step": "validation",
    }
