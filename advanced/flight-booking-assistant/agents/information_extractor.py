from datetime import datetime
from utils.prompts import SYSTEM_PERSONA, EXTRACTION_PROMPT, PNR_EXTRACTION_PROMPT, format_history
from utils.llm import call_llm_json

_PNR_PROCESSES = {"web_checkin", "flight_status"}


def information_extractor_agent(state):
    print(f"\n[DEBUG] information_extractor_agent called")

    user_input = state.get("last_user_input", "")
    process = state.get("process", "")

    if not user_input:
        return state

    # ── PNR extraction ────────────────────────────────────────────────────────
    if process in _PNR_PROCESSES:
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

    # ── Flight booking extraction ─────────────────────────────────────────────
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

        # Smart city assignment logic
        if extracted.get("departure_city") or extracted.get("destination_city"):
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
        print(f"[DEBUG] Extracted {extracted_count} field(s), cities_updated={cities_updated}")

    except Exception as e:
        print(f"[DEBUG] Extraction error: {e}")

    state["extraction_attempted"] = True
    state["step"] = "EXTRACTED"
    return state
