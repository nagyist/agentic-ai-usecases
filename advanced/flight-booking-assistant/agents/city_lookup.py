import time
from utils.prompts import SYSTEM_PERSONA, CITY_LOOKUP_PROMPT
from utils.llm import call_llm_json, log_node
from utils.db import get_candidate_cities, city_to_code

_CITY_FIELDS = ["departure_city", "destination_city"]


def _resolve(city: str) -> tuple[str | None, list[str]]:
    """Return (resolved_name_or_None, candidates)."""
    candidates = get_candidate_cities(city)
    if not candidates:
        return None, []

    prompt = CITY_LOOKUP_PROMPT.format(
        system=SYSTEM_PERSONA,
        input_city=city,
        candidates=", ".join(candidates),
    )
    try:
        result = call_llm_json(prompt)
        resolved = result.get("resolved_city")
        return resolved, candidates
    except Exception as e:
        print(f"[DEBUG] city_lookup LLM error: {e}")
        return None, candidates


def city_lookup_agent(state: dict) -> dict:
    print(f"\n[DEBUG] city_lookup_agent called")
    t0 = time.time()
    errors = []
    resolutions = {}

    for field in state.get("cities_changed", []):
        raw = state.get(field)
        if not raw:
            continue

        resolved, candidates = _resolve(raw)
        print(f"[DEBUG] city_lookup '{raw}' → resolved='{resolved}', candidates={candidates}")

        if resolved:
            state[field] = resolved.title()
            code = city_to_code(resolved)
            code_field = "departure_airport_code" if field == "departure_city" else "destination_airport_code"
            state[code_field] = code
            resolutions[field] = {"input": raw, "resolved": state[field], "iata": code, "candidates": candidates}
            print(f"[DEBUG] city_lookup: {field} normalised to '{state[field]}' ({code})")
        else:
            label = "departure" if field == "departure_city" else "destination"
            errors.append(
                f"Sorry, '{raw}' does not appear to have a serviced airport. "
                f"Please provide a valid {label} city."
            )
            resolutions[field] = {"input": raw, "resolved": None, "candidates": candidates}
            state[field] = None
            print(f"[DEBUG] city_lookup: cleared {field} (no airport found)")

    if errors:
        state["city_error"] = " ".join(errors)
    else:
        state["city_error"] = ""

    state["step"] = "CITY_VALIDATED"

    log_node("city_lookup", {
        "resolutions": resolutions,
        "errors": errors,
        "outcome": "errors" if errors else "ok",
    }, latency_ms=round((time.time() - t0) * 1000))

    return state
