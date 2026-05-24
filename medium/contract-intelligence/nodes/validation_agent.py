import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.state import ContractState
from config.settings import BASE_DIR

RULES_PATH = BASE_DIR / "config" / "business_rules.yaml"

_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
    "%B %d, %Y", "%d %B %Y", "%b %d, %Y", "%d %b %Y",
    "%Y/%m/%d",
]


def _parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_price(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_days(text: Any) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"\b(\d+)\s*(?:days?|d)\b", str(text), re.IGNORECASE)
    return int(m.group(1)) if m else None


def _load_custom_rules() -> List[Dict]:
    if RULES_PATH.exists():
        with open(RULES_PATH) as f:
            data = yaml.safe_load(f) or {}
            return data.get("rules", [])
    return []


# ── Node ─────────────────────────────────────────────────────────────────────

def validation_agent_node(state: ContractState) -> dict:
    log = list(state.get("processing_log", []))
    fields = state.get("extracted_fields", {})
    results: Dict[str, Dict] = {}

    def _record(rule_id: str, passed: bool, severity: str, message: str, field: str) -> None:
        results[rule_id] = {
            "passed": passed,
            "severity": severity if not passed else "ok",
            "message": message,
            "field": field,
        }

    # ── 1. Required-field presence ───────────────────────────────────────────
    required = [
        "party_a_legal_name", "party_b_legal_name",
        "start_date", "end_date", "payment_timeline",
    ]
    for f in required:
        val = fields.get(f, {}).get("value")
        _record(
            f"required_{f}",
            passed=bool(val),
            severity="error",
            message=f"'{f}' extracted successfully" if val else f"Required field '{f}' not found",
            field=f,
        )

    # ── 2. Date order: end > start ────────────────────────────────────────────
    start_str = fields.get("start_date", {}).get("value")
    end_str = fields.get("end_date", {}).get("value")
    start_dt = _parse_date(start_str)
    end_dt = _parse_date(end_str)

    if start_dt and end_dt:
        ok = end_dt > start_dt
        _record(
            "date_order",
            passed=ok,
            severity="error",
            message=(
                f"End Date ({end_str}) is after Start Date ({start_str})"
                if ok
                else f"End Date ({end_str}) must be after Start Date ({start_str})"
            ),
            field="start_date",
        )
    elif start_dt or end_dt:
        _record(
            "date_order",
            passed=False,
            severity="warning",
            message="Could not compare dates – one or both dates missing/unparseable",
            field="start_date",
        )

    # ── 3. Price validity within contract period ──────────────────────────────
    validity_str = fields.get("price_validity_period", {}).get("value")
    validity_dt = _parse_date(validity_str)
    if validity_dt and end_dt:
        ok = validity_dt <= end_dt
        _record(
            "price_validity_within_contract",
            passed=ok,
            severity="warning",
            message=(
                f"Price validity ({validity_str}) is within contract end ({end_str})"
                if ok
                else f"Price validity ({validity_str}) extends beyond contract end ({end_str})"
            ),
            field="price_validity_period",
        )

    # ── 4. Price values positive ──────────────────────────────────────────────
    price_data = fields.get("price_details", {})
    price_items = price_data.get("value", [])
    price_columns = price_data.get("columns", [])
    price_col = next(
        (c for c in price_columns if "price" in c.lower()),
        next((c for c in price_columns if any(k in c.lower() for k in ("rate", "cost", "amount", "fee", "srp"))), None),
    )
    if isinstance(price_items, list):
        for i, item in enumerate(price_items):
            raw = item.get(price_col) if price_col else item.get("price")
            p = _parse_price(raw)
            label = next((item.get(c) for c in price_columns if c != price_col and item.get(c)), i)
            if p is not None and p <= 0:
                _record(
                    f"price_positive_item_{i}",
                    passed=False,
                    severity="error",
                    message=f"Price item '{label}' has non-positive value: {p}",
                    field="price_details",
                )

    # ── 5. Custom YAML rules ──────────────────────────────────────────────────
    for rule in _load_custom_rules():
        rule_id = rule.get("id", "custom")
        severity = rule.get("severity", "warning")

        if rule_id == "payment_term_max":
            payment_text = fields.get("payment_timeline", {}).get("value", "")
            days = _extract_days(payment_text)
            max_days = rule.get("max_days", 90)
            if days is not None:
                ok = days <= max_days
                _record(
                    rule_id,
                    passed=ok,
                    severity=severity,
                    message=(
                        f"Payment timeline ({days} days) is within {max_days}-day limit"
                        if ok
                        else f"Payment timeline ({days} days) exceeds {max_days}-day limit"
                    ),
                    field="payment_timeline",
                )

        elif rule_id == "min_contract_duration":
            if start_dt and end_dt:
                duration = (end_dt - start_dt).days
                min_days = rule.get("min_days", 30)
                ok = duration >= min_days
                _record(
                    rule_id,
                    passed=ok,
                    severity=severity,
                    message=(
                        f"Contract duration ({duration} days) meets minimum ({min_days} days)"
                        if ok
                        else f"Contract duration ({duration} days) is below minimum ({min_days} days)"
                    ),
                    field="start_date",
                )

    all_passed = all(v["passed"] for v in results.values())
    fail_count = sum(1 for v in results.values() if not v["passed"])
    log.append(
        f"Validation: {'PASSED' if all_passed else f'{fail_count} issue(s) found'} "
        f"({len(results)} checks run)"
    )

    return {
        **state,
        "validation_results": results,
        "validation_passed": all_passed,
        "processing_log": log,
        "current_step": "excel_generation",
    }
