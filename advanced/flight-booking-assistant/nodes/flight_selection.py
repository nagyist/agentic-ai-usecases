from utils.prompts import FLIGHT_SELECTION_PROMPT, SYSTEM_PERSONA
from utils.llm import call_llm_json
from utils.db import get_airport_name
from utils.formatting import format_date


def select_flight(state: dict) -> dict:
    print(f"\n[DEBUG] select_flight called")

    flights = state.get("flights", [])
    user_input = state.get("last_user_input", "")

    if not flights:
        state["assistant_message"] = "Sorry, I could not find any flights. Please try different dates."
        state["step"] = "COLLECT_SLOTS"
        state["current_agent"] = "flight_selection"
        return state

    prompt = FLIGHT_SELECTION_PROMPT.format(
        system=SYSTEM_PERSONA,
        flights=flights,
        user_input=user_input,
    )

    selected = None
    try:
        result = call_llm_json(prompt)
        idx = result.get("selected_index")
        if idx is not None and 0 <= int(idx) < len(flights):
            selected = flights[int(idx)]
    except Exception as e:
        print(f"[DEBUG] flight selection LLM error: {e}")

    if selected is None:
        state["assistant_message"] = (
            "I could not identify your selection. "
            "Please say something like 'flight 1', 'the cheapest', or the departure time."
        )
        state["step"] = "SHOW_FLIGHTS"
        state["current_agent"] = "flight_selection"
        return state

    # Show flight details and ask for confirmation
    booking_leg = state.get("booking_leg") or "outbound"
    origin_name = get_airport_name(selected.get("origin", ""))
    dest_name = get_airport_name(selected.get("destination", ""))
    if booking_leg == "return":
        date_display = format_date(state.get("return_date", ""))
        leg_label = "Return"
    else:
        date_display = format_date(state.get("travel_date", ""))
        leg_label = "Outbound"

    response = (
        f"Please review the selected {leg_label.lower()} flight details:\n\n"
        f"Departure   : {origin_name} ({selected.get('origin')})\n"
        f"Destination : {dest_name} ({selected.get('destination')})\n"
        f"Travel Date : {date_display}\n"
        f"{selected['departure_time']} -- {selected['duration']} -- {selected['arrival_time']}\n"
        f"Fare        : Rs.{selected['price']}\n"
        f"Non-stop\n"
        f"Flight      : {selected['flight_number']}\n\n"
        f"Please confirm your IndiGo {selected['flight_number']} flight.\n"
        "Option - Yes\n"
        "Option - No"
    )

    state["selected_flight"] = selected
    if booking_leg == "return":
        state["selected_return_flight"] = selected
    state["assistant_message"] = response
    state["step"] = "flight_confirm"
    state["confirmation_step"] = "flight_confirm"
    state["current_agent"] = "flight_selection"
    return state
