import time
from utils.db import fetch_flights
from utils.formatting import format_date
from utils.llm import log_node


def flight_search_agent(state: dict) -> dict:
    print(f"\n[DEBUG] flight_search_agent called")
    t0 = time.time()

    booking_leg = state.get("booking_leg") or "outbound"
    if booking_leg == "return":
        departure = state.get("destination_city", "")
        destination = state.get("departure_city", "")
        search_date = state.get("return_date", "")
    else:
        departure = state.get("departure_city", "")
        destination = state.get("destination_city", "")
        search_date = state.get("travel_date", "")

    flights = fetch_flights(departure, destination)

    if not flights:
        log_node("flight_search", {
            "route": f"{departure} → {destination}",
            "travel_date": search_date,
            "flights_found": 0,
            "outcome": "no_flights",
        }, latency_ms=round((time.time() - t0) * 1000))
        state["assistant_message"] = (
            "Sorry, no flights found for that route and date. "
            "Please try a different date or route."
        )
        state["step"] = "COLLECT_SLOTS"
        state["current_agent"] = "search"
        return state

    date_display = format_date(search_date)
    leg_label = "return flights" if booking_leg == "return" else "flights"
    text = (
        f"Congratulations! You are receiving a discounted fare with IndiGo's 6Exclusive offer.\n\n"
        f"Available {leg_label} on {date_display} ({departure} → {destination}):\n\n"
    )
    for i, f in enumerate(flights, 1):
        text += (
            f"-----\nFlight {i}\n"
            f"{f['departure_time']} -- {f['duration']} -- {f['arrival_time']}\n"
            f"Starts at Rs.{f['price']}\n"
            f"Non-stop\n"
            f"{f['flight_number']}\n"
            f"-----\n\n"
        )
    text += "Please choose the flight you wish to book.\neg. flight 1, cheapest flight, 9:00 AM"

    state["flights"] = flights
    state["assistant_message"] = text
    state["step"] = "SHOW_FLIGHTS"
    state["current_agent"] = "search"
    log_node("flight_search", {
        "route": f"{departure} → {destination}",
        "travel_date": state.get("travel_date"),
        "flights_found": len(flights),
        "flight_numbers": [f["flight_number"] for f in flights],
        "outcome": "ok",
    }, latency_ms=round((time.time() - t0) * 1000))
    return state
