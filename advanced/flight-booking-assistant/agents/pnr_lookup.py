from utils.db import fetch_pnr_info


def pnr_lookup_agent(state: dict) -> dict:
    print(f"\n[DEBUG] pnr_lookup_agent called, process={state.get('process')}")

    pnr = state.get("pnr", "").strip().upper()
    process = state.get("process", "")
    state["current_agent"] = "pnr_lookup"

    if not pnr:
        state["assistant_message"] = "I could not find a PNR number in your message. Please provide your 6-character PNR code."
        state["step"] = "COLLECT_PNR"
        return state

    info = fetch_pnr_info(pnr)

    if not info:
        state["assistant_message"] = (
            f"We could not find any booking with PNR {pnr}. "
            "Please check the PNR and try again, or type 'exit' to return to the main menu."
        )
        state["step"] = "COLLECT_PNR"
        state["pnr"] = ""
        return state

    if process == "flight_status":
        state["assistant_message"] = _format_flight_status(info)
    else:  # web_checkin
        state["assistant_message"] = _format_web_checkin(info)

    state["step"] = "PNR_DONE"
    return state


def _format_flight_status(info: dict) -> str:
    pax_lines = ""
    for p in info.get("passengers", []):
        pax_lines += f"\n  - {p['first_name']} {p['last_name']} ({p['passenger_type']})"

    live = info.get("live_status", "Scheduled")
    actual_dep = info.get("actual_departure", "")
    actual_arr = info.get("actual_arrival", "")

    timing_line = ""
    if actual_dep:
        timing_line = f"\nActual Departure : {str(actual_dep)[:16]}"
    if actual_arr:
        timing_line += f"\nActual Arrival   : {str(actual_arr)[:16]}"

    return (
        f"Flight Status for PNR {info['pnr_code']}\n"
        "-----------------------------------\n"
        f"Flight      : {info['flight_id']}\n"
        f"Date        : {info['flight_date']}\n"
        f"From        : {info['origin']} — {info['origin_airport']}\n"
        f"To          : {info['destination']} — {info['destination_airport']}\n"
        f"Departure   : {info['departure_time']}\n"
        f"Arrival     : {info['arrival_time']}\n"
        f"Duration    : {info['duration']}\n"
        f"Status      : {live}{timing_line}\n"
        "-----------------------------------\n"
        f"PNR Status  : {info['pnr_status'].title()}\n"
        f"Booking     : {info['booking_status'].title()}\n"
        f"Passengers  :{pax_lines if pax_lines else ' —'}\n\n"
        "Type 'exit' to return to the main menu."
    )


def _format_web_checkin(info: dict) -> str:
    pax_lines = ""
    for p in info.get("passengers", []):
        pax_lines += f"\n  - {p['first_name']} {p['last_name']} ({p['passenger_type']})"

    booking_status = info.get("booking_status", "").lower()

    if booking_status != "confirmed":
        return (
            f"Web check-in is not available for PNR {info['pnr_code']}.\n"
            f"Booking status is '{info['booking_status'].title()}'. "
            "Only confirmed bookings are eligible for web check-in.\n\n"
            "Type 'exit' to return to the main menu."
        )

    return (
        f"Web Check-in Details for PNR {info['pnr_code']}\n"
        "-----------------------------------\n"
        f"Flight      : {info['flight_id']}\n"
        f"Date        : {info['flight_date']}\n"
        f"From        : {info['origin']} — {info['origin_airport']}\n"
        f"To          : {info['destination']} — {info['destination_airport']}\n"
        f"Departure   : {info['departure_time']}\n"
        f"Arrival     : {info['arrival_time']}\n"
        "-----------------------------------\n"
        f"Passengers  :{pax_lines if pax_lines else ' —'}\n\n"
        "Web check-in opens 48 hours before departure and closes 60 minutes before departure.\n"
        "Please visit goindigo.in to complete your check-in.\n\n"
        "Type 'exit' to return to the main menu."
    )
