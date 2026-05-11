from datetime import datetime
from utils.prompts import (
    SYSTEM_PERSONA,
    EXTRACTION_PROMPT,
    PASSENGER_EXTRACTION_PROMPT,
    PNR_EXTRACTION_PROMPT,
    format_history,
)
from utils.llm import call_llm_json

_PNR_PROCESSES = {"web_checkin", "flight_status"}
_PASSENGER_STEPS = {"flight_confirm", "whatsapp_consent", "collect_names", "collect_email"}


def information_extractor_agent(state):
    print(f"\n[DEBUG] information_extractor_agent called")

    user_input = state.get("last_user_input", "")
    process = state.get("process", "")

    if not user_input:
        return state

    # ── PNR extraction ────────────────────────────────────────────────────────
    if process in _PNR_PROCESSES:
        return _extract_pnr(state)

    # ── Passenger info extraction (Phase 2) ───────────────────────────────────
    if state.get("confirmation_step") in _PASSENGER_STEPS:
        return _extract_passenger_info(state)

    # ── Flight booking slot extraction (Phase 1) ──────────────────────────────
    return _extract_flight_slots(state)


def _extract_pnr(state: dict) -> dict:
    user_input = state.get("last_user_input", "")
    prompt = PNR_EXTRACTION_PROMPT.format(
        system=SYSTEM_PERSONA,
        user_input=user_input,
    )
    try:
        extracted = call_llm_json(prompt)
        pnr = extracted.get("pnr")
        if pnr:
            state["pnr"] = pnr.strip().upper()
            print(f"[DEBUG] Extracted PNR: {state['pnr']}")
        else:
            print("[DEBUG] No PNR found in user input")
    except Exception as e:
        print(f"[DEBUG] PNR extraction error: {e}")

    state["step"] = "PNR_EXTRACTED"
    return state


def _extract_passenger_info(state: dict) -> dict:
    confirmation_step = state.get("confirmation_step", "")
    user_input = state.get("last_user_input", "")

    prompt = PASSENGER_EXTRACTION_PROMPT.format(
        system=SYSTEM_PERSONA,
        current_step=confirmation_step,
        user_input=user_input,
    )
    try:
        extracted = call_llm_json(prompt)
        print(f"[DEBUG] Passenger extracted: {extracted}")

        if confirmation_step == "flight_confirm":
            val = extracted.get("flight_confirmed")
            if val is not None:
                state["flight_confirmed"] = val

        elif confirmation_step == "whatsapp_consent":
            val = extracted.get("whatsapp_consent")
            if val is not None:
                state["whatsapp_consent"] = val

        elif confirmation_step == "collect_names":
            val = extracted.get("passenger_names")
            if val:
                state["passenger_names"] = val

        elif confirmation_step == "collect_email":
            val = extracted.get("email")
            if val:
                state["email"] = val

    except Exception as e:
        print(f"[DEBUG] Passenger extraction error: {e}")

    state["cities_updated"] = False
    state["current_agent"] = "info_extractor"
    return state


def _extract_flight_slots(state: dict) -> dict:
    user_input = state.get("last_user_input", "")
    history = format_history(state.get("messages", []))
    extraction_prompt = EXTRACTION_PROMPT.format(
        system=SYSTEM_PERSONA,
        today_date=datetime.today().strftime("%Y-%m-%d"),
        conversation_history=history,
        user_input=user_input,
    )

    try:
        extracted = call_llm_json(extraction_prompt)
        print(f"[DEBUG] Extracted: {extracted}")

        # Smart city assignment — only when exactly one city is extracted.
        # If both are present the LLM already assigned them correctly; don't touch.
        has_departure = bool(extracted.get("departure_city"))
        has_destination = bool(extracted.get("destination_city"))
        if (has_departure or has_destination) and not (has_departure and has_destination):
            extracted_city = extracted.get("departure_city") or extracted.get("destination_city")

            if extracted_city and state.get("destination_city") and extracted_city != state.get("destination_city"):
                print(f"[DEBUG] Reassigning '{extracted_city}' to departure_city (we already have destination)")
                extracted["departure_city"] = extracted_city
                extracted["destination_city"] = None
            elif extracted_city and state.get("departure_city") and extracted_city != state.get("departure_city"):
                print(f"[DEBUG] Reassigning '{extracted_city}' to destination_city (we already have departure)")
                extracted["destination_city"] = extracted_city
                extracted["departure_city"] = None

        extracted_count = 0
        cities_updated = False
        for key, value in extracted.items():
            if value:
                print(f"[DEBUG] Updating {key} = {value}")
                state[key] = value
                extracted_count += 1
                if key in ("departure_city", "destination_city"):
                    cities_updated = True

        state["cities_updated"] = cities_updated
        state["slots_updated"] = extracted_count > 0
        print(f"[DEBUG] Extracted {extracted_count} field(s), cities_updated={cities_updated}")

    except Exception as e:
        print(f"[DEBUG] Extraction error: {e}")

    state["extraction_attempted"] = True
    state["step"] = "EXTRACTED"
    return state
