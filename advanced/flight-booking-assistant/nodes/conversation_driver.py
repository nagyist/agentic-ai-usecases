import re
import time
from datetime import datetime, timedelta
from utils.prompts.conversation import SYSTEM_PERSONA, RETRY_MESSAGE_PROMPT
from utils.llm import call_llm, log_node
from utils.formatting import format_date, format_passengers
from config import MAX_SLOT_ATTEMPTS, TERMINATION_MESSAGE
from utils.user_messages import (
    SLOT_QUESTIONS, SLOT_LABELS, TRAVEL_DATE_QUESTION, RETURN_DATE_QUESTION,
    PNR_PROMPTS, WHATSAPP_CONSENT_MESSAGE, PASSENGER_NAME_MESSAGE,
    EMAIL_MESSAGE, FLIGHT_CONFIRM_REASK,
)


_PASSENGER_STEPS = {"flight_confirm", "whatsapp_consent", "collect_names", "collect_email"}


def _generate_retry_message(slot_label: str, error: str, user_input: str) -> str:
    prompt = RETRY_MESSAGE_PROMPT.format(
        system=SYSTEM_PERSONA,
        slot_label=slot_label,
        error=error,
        user_input=user_input,
    )
    return call_llm(prompt)


def drive_conversation(state: dict) -> dict:
    print(f"\n[DEBUG] drive_conversation called")

    process = state.get("process", "")

    # ── PNR collection flow (web_checkin / flight_status) ────────────────────
    if process in PNR_PROMPTS:
        if not state.get("pnr"):
            state["assistant_message"] = PNR_PROMPTS[process]
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
    t0 = time.time()
    confirmation_step = state.get("confirmation_step", "")
    print(f"[DEBUG] passenger_driver: confirmation_step={confirmation_step}")

    if confirmation_step == "flight_confirm":
        flight_confirmed = state.get("flight_confirmed")
        if flight_confirmed is True:
            is_round_trip = state.get("trip_type") == "round-trip"
            is_outbound = (state.get("booking_leg") or "outbound") != "return"
            if is_round_trip and is_outbound:
                state["selected_outbound_flight"] = state.get("selected_flight", {})
                state["selected_flight"] = {}
                state["flights"] = []
                state["flight_confirmed"] = None
                state["booking_leg"] = "return"
                state["confirmation_step"] = "flight_confirm"
                state["step"] = "SEARCH_RETURN_FLIGHTS"
                state["assistant_message"] = "Great! Now let's find your return flight."
            else:
                state["assistant_message"] = WHATSAPP_CONSENT_MESSAGE
                state["confirmation_step"] = "whatsapp_consent"
                state["step"] = "whatsapp_consent"
        elif flight_confirmed is False:
            state["step"] = "SHOW_FLIGHTS"
            state["confirmation_step"] = ""
            state["assistant_message"] = (
                "No problem. Here are the available flights again. Please choose one."
            )
        else:
            state["assistant_message"] = FLIGHT_CONFIRM_REASK

    elif confirmation_step == "whatsapp_consent":
        consent = state.get("whatsapp_consent")
        if consent is None:
            state["assistant_message"] = WHATSAPP_CONSENT_MESSAGE
        else:
            state["assistant_message"] = PASSENGER_NAME_MESSAGE
            state["confirmation_step"] = "collect_names"
            state["step"] = "collect_names"

    elif confirmation_step == "collect_names":
        passengers = state.get("passengers") or []
        passenger_error = state.get("passenger_error", "")
        state["passenger_error"] = ""
        adults = state.get("adults") or 0
        children = state.get("children") or 0
        expected = adults + children
        if len(passengers) < expected:
            name_attempts = state.get("name_attempts", 0) + 1
            state["name_attempts"] = name_attempts
            if name_attempts > MAX_SLOT_ATTEMPTS:
                state["terminated"] = True
                state["assistant_message"] = TERMINATION_MESSAGE
            elif passengers:
                collected = ", ".join(
                    f"{p['title']} {p['first_name']} {p['last_name']}" for p in passengers
                )
                remaining = expected - len(passengers)
                state["assistant_message"] = (
                    f"Got it! I have recorded: {collected}.\n\n"
                    f"Please provide the name(s) for the remaining {remaining} passenger(s).\n"
                    "eg: Mr./Mrs./Miss First Name Last Name"
                )
            elif name_attempts > 1 and passenger_error:
                state["assistant_message"] = _generate_retry_message(
                    "passenger names", passenger_error, state.get("last_user_input", "")
                )
            else:
                state["assistant_message"] = PASSENGER_NAME_MESSAGE
        else:
            state["name_attempts"] = 0
            state["assistant_message"] = EMAIL_MESSAGE
            state["confirmation_step"] = "collect_email"
            state["step"] = "collect_email"

    elif confirmation_step == "collect_email":
        email = state.get("email", "")
        passenger_error = state.get("passenger_error", "")
        state["passenger_error"] = ""
        if not email:
            prefix = f"{passenger_error}\n\n" if passenger_error else ""
            state["assistant_message"] = f"{prefix}{EMAIL_MESSAGE}"
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            state["email"] = ""
            state["assistant_message"] = _generate_retry_message(
                "email address",
                "The provided email address format was invalid.",
                state.get("last_user_input", ""),
            )
        else:
            state["step"] = "PAYMENT"
            state["confirmation_step"] = "complete"
            state["assistant_message"] = ""

    state["current_agent"] = "conversation_driver"
    log_node("conversation_driver._drive_passenger_collection", {
        "confirmation_step": confirmation_step,
        "next_step": state.get("step"),
        "flight_confirmed": state.get("flight_confirmed"),
        "whatsapp_consent": state.get("whatsapp_consent"),
        "passenger_names": state.get("passenger_names") or None,
        "email": state.get("email") or None,
    }, latency_ms=round((time.time() - t0) * 1000))
    return state



def _drive_flight_slots(state: dict) -> dict:
    t0 = time.time()

    if any(v > MAX_SLOT_ATTEMPTS for v in state.get("slot_attempts", {}).values()):
        state["terminated"] = True
        state["assistant_message"] = TERMINATION_MESSAGE
        state["current_agent"] = "conversation_driver"
        return state

    slot_error = state.get("slot_error", "")
    state["slot_error"] = ""
    city_error = state.get("city_error", "")
    state["city_error"] = ""

    errors = "\n".join(e for e in [slot_error, city_error] if e)

    missing = _get_missing_flight_slots(state)
    print(f"[DEBUG] missing slots: {missing}")

    if not missing:
        children = state.get("children") or 0
        children_text = f", {children} Child(ren)" if children > 0 else ""
        date_display = format_date(state.get("travel_date", ""))

        return_date_line = ""
        if state.get("trip_type") == "round-trip" and state.get("return_date"):
            return_date_line = f"\nReturn Date : {format_date(state['return_date'])}"

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
        log_node("conversation_driver._drive_flight_slots", {
            "outcome": "all_slots_collected",
            "next_step": "CONFIRM_BOOKING",
            "errors_shown": errors or None,
        }, latency_ms=round((time.time() - t0) * 1000))
        return state

    today = datetime.today()
    next_slot = missing[0]
    question = _ask_for_slot(next_slot, today)
    if errors:
        state["assistant_message"] = _generate_retry_message(
            SLOT_LABELS.get(next_slot, next_slot),
            errors,
            state.get("last_user_input", ""),
        )
    else:
        state["assistant_message"] = question
    state["step"] = "COLLECT_SLOTS"
    state["current_agent"] = "conversation_driver"
    log_node("conversation_driver._drive_flight_slots", {
        "outcome": "asking_for_slot",
        "missing_slots": missing,
        "next_asking": next_slot,
        "errors_shown": errors or None,
        "next_step": "COLLECT_SLOTS",
    }, latency_ms=round((time.time() - t0) * 1000))
    return state


def _get_missing_flight_slots(state: dict) -> list:
    missing = []
    for s in ["destination_city", "departure_city", "travel_date", "trip_type"]:
        if not state.get(s):
            missing.append(s)
    if state.get("trip_type") == "round-trip" and not state.get("return_date"):
        missing.append("return_date")
    if not state.get("adults") or state.get("children") is None:
        missing.append("passengers")
    return missing



def _ask_for_slot(slot: str, today: datetime) -> str:
    if slot == "travel_date":
        example = (today + timedelta(days=5)).strftime("%d %B")
        return TRAVEL_DATE_QUESTION.format(example=example)
    if slot == "return_date":
        example = (today + timedelta(days=12)).strftime("%d %B")
        return RETURN_DATE_QUESTION.format(example=example)
    return SLOT_QUESTIONS.get(slot, f"Please provide your {slot}.")


