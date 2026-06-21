import time
from datetime import date
from utils.llm import log_node


def validate_slots(state: dict) -> dict:
    t0 = time.time()
    errors = []
    fields_cleared = []

    travel_date_str = state.get("travel_date")
    if travel_date_str:
        try:
            td = date.fromisoformat(travel_date_str)
            if td < date.today():
                errors.append(f"Travel date {travel_date_str} is in the past. Please provide a future date.")
                state["travel_date"] = None
                fields_cleared.append("travel_date")
        except ValueError:
            errors.append(f"'{travel_date_str}' is not a valid date. Please provide a date like 25 June.")
            state["travel_date"] = None
            fields_cleared.append("travel_date")

    return_date_str = state.get("return_date")
    if state.get("trip_type") == "round-trip" and return_date_str:
        try:
            rd = date.fromisoformat(return_date_str)
            travel_date_ok = state.get("travel_date")
            if travel_date_ok:
                if rd < date.fromisoformat(travel_date_ok):
                    errors.append(
                        f"Return date {return_date_str} cannot be before travel date {travel_date_ok}."
                    )
                    state["return_date"] = None
                    fields_cleared.append("return_date")
            elif rd < date.today():
                errors.append(f"Return date {return_date_str} is in the past. Please provide a future date.")
                state["return_date"] = None
                fields_cleared.append("return_date")
        except ValueError:
            errors.append(f"'{return_date_str}' is not a valid return date.")
            state["return_date"] = None
            fields_cleared.append("return_date")

    adults = state.get("adults")
    if adults is not None and adults < 1:
        errors.append("At least 1 adult passenger is required.")
        state["adults"] = None
        fields_cleared.append("adults")

    children = state.get("children")
    if children is not None and children < 0:
        errors.append("Number of children cannot be negative.")
        state["children"] = None
        fields_cleared.append("children")

    state["slot_error"] = "\n".join(errors) if errors else ""
    state["current_agent"] = "slot_validator"
    print(f"[DEBUG] validate_slots: errors={errors}")

    log_node("slot_validator", {
        "fields_checked": {
            "travel_date": travel_date_str,
            "return_date": return_date_str,
            "adults": adults,
            "children": children,
        },
        "errors": errors,
        "fields_cleared": fields_cleared,
        "outcome": "invalid" if errors else "valid",
    }, latency_ms=round((time.time() - t0) * 1000))

    return state
