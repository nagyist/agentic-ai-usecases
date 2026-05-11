import re
from datetime import datetime, timedelta
from utils.prompts import WHATSAPP_PROMPT, PASSENGER_PROMPT, EMAIL_PROMPT


_PASSENGER_STEPS = {"flight_confirm", "whatsapp_consent", "collect_names", "collect_email"}

_PNR_PROMPTS = {
    "web_checkin":   "To initiate web check-in process, please provide your PNR number.",
    "flight_status": "To check your flight status and terminal, please provide your PNR number.",
}


def conversation_driver_agent(state: dict) -> dict:
    print(f"\n[DEBUG] conversation_driver_agent called")

    process = state.get("process", "")

    # ── PNR collection flow (web_checkin / flight_status) ────────────────────
    if process in _PNR_PROMPTS:
        if not state.get("pnr"):
            state["assistant_message"] = _PNR_PROMPTS[process]
            state["step"] = "COLLECT_PNR"
            state["current_agent"] = "conversation_driver"
            return state
        return state

    # ── Passenger collection (Phase 2) ───────────────────────────────────────
    if state.get("confirmation_step") in _PASSENGER_STEPS:
        return _drive_passenger_collection(state)

    # ── Flight slot collection (Phase 1) ─────────────────────────────────────
    return _drive_flight_slots(state)


def _drive_passenger_collection(state: dict) -> dict:
    confirmation_step = state.get("confirmation_step", "")
    print(f"[DEBUG] passenger_driver: confirmation_step={confirmation_step}")

    if confirmation_step == "flight_confirm":
        flight_confirmed = state.get("flight_confirmed")
        if flight_confirmed is True:
            state["assistant_message"] = WHATSAPP_PROMPT
            state["confirmation_step"] = "whatsapp_consent"
            state["step"] = "whatsapp_consent"
        elif flight_confirmed is False:
            state["step"] = "SHOW_FLIGHTS"
            state["confirmation_step"] = ""
            state["assistant_message"] = (
                "No problem. Here are the available flights again. Please choose one."
            )
        else:
            state["assistant_message"] = (
                "Please reply Yes to confirm the flight or No to pick a different one.\n"
                "Option - Yes\n"
                "Option - No"
            )

    elif confirmation_step == "whatsapp_consent":
        consent = state.get("whatsapp_consent")
        if consent is None:
            # Extractor could not parse yes/no — re-ask
            state["assistant_message"] = WHATSAPP_PROMPT
        else:
            state["assistant_message"] = PASSENGER_PROMPT
            state["confirmation_step"] = "collect_names"
            state["step"] = "collect_names"

    elif confirmation_step == "collect_names":
        names = state.get("passenger_names", "")
        passenger_error = state.get("passenger_error", "")
        state["passenger_error"] = ""
        if not names:
            prefix = f"{passenger_error}\n\n" if passenger_error else ""
            state["assistant_message"] = f"{prefix}{PASSENGER_PROMPT}"
        else:
            state["assistant_message"] = EMAIL_PROMPT
            state["confirmation_step"] = "collect_email"
            state["step"] = "collect_email"

    elif confirmation_step == "collect_email":
        email = state.get("email", "")
        passenger_error = state.get("passenger_error", "")
        state["passenger_error"] = ""
        if not email:
            prefix = f"{passenger_error}\n\n" if passenger_error else ""
            state["assistant_message"] = f"{prefix}{EMAIL_PROMPT}"
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            # Invalid format — clear and re-ask
            state["email"] = ""
            state["assistant_message"] = (
                "That does not look like a valid email address.\n\n" + EMAIL_PROMPT
            )
        else:
            state["step"] = "PAYMENT"
            state["confirmation_step"] = "complete"

    state["current_agent"] = "conversation_driver"
    return state


def _drive_flight_slots(state: dict) -> dict:
    city_error = state.get("city_error", "")
    if city_error:
        state["city_error"] = ""

    missing = _get_missing_flight_slots(state)
    print(f"[DEBUG] missing slots: {missing}")

    if not missing:
        children = state.get("children") or 0
        children_text = f", {children} Child(ren)" if children > 0 else ""
        date_display = _format_date(state.get("travel_date", ""))

        return_date_line = ""
        if state.get("trip_type") == "round-trip" and state.get("return_date"):
            return_date_line = f"\nReturn Date : {_format_date(state['return_date'])}"

        summary = (
            "Please review your travel details:\n\n"
            f"Departure   : {state.get('departure_city')}\n"
            f"Destination : {state.get('destination_city')}\n"
            f"Travel Date : {date_display}{return_date_line}\n"
            f"Trip Type   : {state.get('trip_type')}\n"
            f"Passengers  : {state.get('adults')} Adult(s){children_text}\n\n"
            "To make changes say something like: change destination to Goa, or 2 adults.\n\n"
            "Please confirm to search for flights.\n"
            "Option - Yes\n"
            "Option - No"
        )
        state["assistant_message"] = summary
        state["step"] = "CONFIRM_BOOKING"
        state["awaiting_confirmation"] = True
        state["current_agent"] = "conversation_driver"
        print(f"[DEBUG] All slots collected, showing confirmation summary")
        return state

    today = datetime.today()
    next_slot = missing[0]
    question = _ask_for_slot(next_slot, today)
    state["assistant_message"] = f"{city_error}\n\n{question}".lstrip() if city_error else question
    state["step"] = "COLLECT_SLOTS"
    state["current_agent"] = "conversation_driver"
    return state


def _get_missing_flight_slots(state: dict) -> list:
    missing = []
    for s in ["destination_city", "departure_city", "travel_date", "trip_type"]:
        if not state.get(s):
            missing.append(s)
    if state.get("trip_type") == "round-trip" and not state.get("return_date"):
        missing.append("return_date")
    if not state.get("adults"):
        missing.append("adults")
    if state.get("children") is None:
        missing.append("children")
    return missing


def _format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B %Y")
    except Exception:
        return date_str


_SLOT_QUESTIONS = {
    "destination_city": "Please let us know your destination city.",
    "departure_city":   "Which city will you be flying from?",
    "trip_type":        "Will this be a one-way or round-trip journey?",
    "adults":           "How many adult passengers will be travelling?",
    "children":         "Will there be any child passengers? (age 2-12 years) If none, please say 0.",
}


def _ask_for_slot(slot: str, today: datetime) -> str:
    if slot == "travel_date":
        example = (today + timedelta(days=5)).strftime("%d %B")
        return f"Which date would you like to travel? (e.g. {example})"
    if slot == "return_date":
        example = (today + timedelta(days=12)).strftime("%d %B")
        return f"What is your return date? (e.g. {example})"
    return _SLOT_QUESTIONS.get(slot, f"Please provide your {slot}.")
