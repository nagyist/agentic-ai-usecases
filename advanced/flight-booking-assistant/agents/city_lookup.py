from utils.prompts import SYSTEM_PERSONA, CITY_LOOKUP_PROMPT
from utils.llm import call_llm_json
from utils.db import get_candidate_cities

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
    errors = []

    for field in _CITY_FIELDS:
        raw = state.get(field)
        if not raw:
            continue  # nothing extracted for this field yet

        resolved, candidates = _resolve(raw)
        print(f"[DEBUG] city_lookup '{raw}' → resolved='{resolved}', candidates={candidates}")

        if resolved:
            # Normalise to the canonical name stored in CITY_TO_CODE
            state[field] = resolved.title()
            print(f"[DEBUG] city_lookup: {field} normalised to '{state[field]}'")
        else:
            # No valid airport city found — clear the field so the driver asks again
            label = "departure" if field == "departure_city" else "destination"
            errors.append(
                f"Sorry, '{raw}' does not appear to have a serviced airport. "
                f"Please provide a valid {label} city."
            )
            state[field] = None
            print(f"[DEBUG] city_lookup: cleared {field} (no airport found)")

    if errors:
        state["city_error"] = " ".join(errors)
    else:
        state["city_error"] = ""

    state["step"] = "CITY_VALIDATED"
    return state
