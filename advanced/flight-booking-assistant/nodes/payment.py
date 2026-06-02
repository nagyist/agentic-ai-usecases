from utils.prompts import PAYMENT_PROMPT
from utils.formatting import format_date, format_flight_block, format_passengers


def payment_agent(state: dict) -> dict:
    print(f"\n[DEBUG] payment_agent called")

    adults = state.get("adults") or 1
    passengers_display = format_passengers(state.get("passengers") or [])
    departure_city = state.get("departure_city", "")
    destination_city = state.get("destination_city", "")

    outbound = state.get("selected_outbound_flight") or {}
    return_flight = state.get("selected_return_flight") or {}
    is_round_trip = bool(outbound and return_flight)

    if is_round_trip:
        outbound_price = outbound.get("price", 0)
        return_price = return_flight.get("price", 0)
        total = (outbound_price + return_price) * adults

        response = (
            "Review Your Booking\n"
            "-----------------------------------\n\n"
            f"{passengers_display}\n\n"
            + format_flight_block(
                f"{departure_city} → {destination_city} (OUTBOUND)",
                outbound,
                format_date(state.get("travel_date", ""), fmt="%d-%m-%Y"),
                adults,
            )
            + "\n"
            + format_flight_block(
                f"{destination_city} → {departure_city} (RETURN)",
                return_flight,
                format_date(state.get("return_date", ""), fmt="%d-%m-%Y"),
                adults,
            )
            + "\n-----------------------------------\n"
            f"Total                        Rs.{total}\n\n"
            "* Convenience fee may apply\n\n"
            "Please proceed with payment via WhatsApp to confirm your booking.\n"
            "Your PNR will be sent after successful payment.\n\n"
            "By continuing, you confirm you have read IndiGo's Privacy Policy:\n"
            "https://www.goindigo.in/information/privacy.html\n\n"
            "The payment link is valid for 10 minutes."
        )
    else:
        flight = state.get("selected_flight", {})
        price = flight.get("price", 0)
        total = price * adults
        response = PAYMENT_PROMPT.format(
            departure_city=departure_city,
            destination_city=destination_city,
            travel_date=format_date(state.get("travel_date", ""), fmt="%d-%m-%Y"),
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
