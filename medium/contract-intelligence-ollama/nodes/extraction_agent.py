from typing import Dict, Any, List

from models.state import ContractState
from services.llm import LLMService
from services.vector_store import HybridVectorStore
from config.settings import EXTRACT_FIELDS, TOP_K_RETRIEVAL

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


def _build_context(results: List[Dict]) -> str:
    return "\n\n".join(
        f"[Excerpt – page {r['metadata'].get('page', 0) + 1}]\n{r['chunk']}"
        for r in results
    )


def _extract_field(
    field: str,
    store: HybridVectorStore,
    llm: LLMService,
) -> Dict[str, Any]:
    # Multi-query retrieval with deduplication
    seen: set = set()
    results: List[Dict] = []
    for q in FIELD_QUERIES[field]:
        for r in store.hybrid_search(q, k=4):
            key = r["chunk"][:80]
            if key not in seen:
                seen.add(key)
                results.append(r)

    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:TOP_K_RETRIEVAL]
    context = _build_context(top)

    if field == "price_details":
        prompt = f"""{FIELD_PROMPTS[field]}

Contract excerpts:
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

Contract excerpts:
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

    # Normalise response structure
    if not response or "value" not in response:
        return {"value": None, "confidence": 0.0, "page_ref": None, "raw_text": ""}

    # Fill in page_ref from retrieval results if model omitted it
    if response.get("page_ref") is None and top:
        response["page_ref"] = top[0]["metadata"].get("page", 0) + 1

    return response


# ── Node ─────────────────────────────────────────────────────────────────────

def extraction_agent_node(state: ContractState) -> dict:
    from nodes.indexing import get_session_store  # avoids circular import at module level

    log = list(state.get("processing_log", []))
    store = get_session_store()
    llm = LLMService()
    extracted: Dict[str, Any] = {}

    for field in EXTRACT_FIELDS:
        try:
            extracted[field] = _extract_field(field, store, llm)
        except Exception as e:
            extracted[field] = {
                "value": None,
                "confidence": 0.0,
                "page_ref": None,
                "raw_text": "",
                "error": str(e),
            }

    found = sum(1 for v in extracted.values() if v.get("value"))
    log.append(f"Extraction complete: {found}/{len(EXTRACT_FIELDS)} fields found")

    return {
        **state,
        "extracted_fields": extracted,
        "processing_log": log,
        "current_step": "validation",
    }
