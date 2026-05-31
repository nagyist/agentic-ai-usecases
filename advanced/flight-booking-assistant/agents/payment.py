from datetime import datetime
from utils.prompts import PAYMENT_PROMPT
from agents.conversation_driver import format_passengers


def _format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return date_str


def payment_agent(state: dict) -> dict:
    print(f"\n[DEBUG] payment_agent called")

    flight = state.get("selected_flight", {})
    adults = state.get("adults") or 1
    price = flight.get("price", 0)
    total = price * adults

    passengers_display = format_passengers(state.get("passengers") or [])

    response = PAYMENT_PROMPT.format(
        departure_city=state.get("departure_city", ""),
        destination_city=state.get("destination_city", ""),
        travel_date=_format_date(state.get("travel_date", "")),
        passengers_display=passengers_display,
        flight_number=flight.get("flight_number", ""),
        departure_time=flight.get("departure_time", ""),
        arrival_time=flight.get("arrival_time", ""),
        duration=flight.get("duration", ""),
        adults=adults,
        price=price,
        total=total,
    )

    state["assistant_message"] = response
    state["step"] = "DONE"
    state["current_agent"] = "payment"
    return state
