from datetime import datetime, timedelta


def _format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B %Y")
    except Exception:
        return date_str


def _get_missing(state: dict) -> list:
    missing = []
    for s in ["destination_city", "departure_city", "travel_date", "trip_type"]:
        if not state.get(s):
            missing.append(s)
    # return_date only required for round-trips
    if state.get("trip_type") == "round-trip" and not state.get("return_date"):
        missing.append("return_date")
    if not state.get("adults"):
        missing.append("adults")
    # children: 0 is valid, so check is None explicitly
    if state.get("children") is None:
        missing.append("children")
    return missing


_PNR_PROMPTS = {
    "web_checkin":  "To initiate web check-in process, please provide your PNR number.",
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
        # PNR present — pnr_lookup_agent will take over via graph routing
        return state
    # ─────────────────────────────────────────────────────────────────────────

    city_error = state.get("city_error", "")
    if city_error:
        state["city_error"] = ""  # consume it

    missing = _get_missing(state)
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
        state["current_agent"] = "conversation_driver"
        print(f"[DEBUG] All slots collected, showing confirmation summary")
        return state

    # Ask for the first missing slot — deterministic, no LLM
    today = datetime.today()
    next_slot = missing[0]
    question = _ask_for_slot(next_slot, today)
    state["assistant_message"] = f"{city_error}\n\n{question}".lstrip() if city_error else question
    state["step"] = "COLLECT_SLOTS"
    state["current_agent"] = "conversation_driver"
    return state


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
