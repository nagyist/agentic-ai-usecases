from services.booking_save import save_booking


def done(state: dict) -> dict:
    print(f"\n[DEBUG] done called")

    result = save_booking(state)
    pnr_code = result.get("pnr_code", "")
    transaction_id = result.get("transaction_id", "")

    print(f"[DEBUG] PNR generated: {pnr_code} | txn: {transaction_id}")

    if pnr_code:
        state["pnr"] = pnr_code
        confirmation = (
            "Booking Confirmed!\n"
            "-----------------------------------\n"
            f"Your PNR: {pnr_code}\n"
            f"Transaction ID: {transaction_id}\n"
            "-----------------------------------\n\n"
            "A confirmation has been sent to your email and WhatsApp.\n"
            "Use your PNR for web check-in or to check flight status.\n\n"
            "Is there anything else I can help you with?\n"
            "- Book a flight ticket\n"
            "- Flight Status\n"
            "- Web Check-in"
        )
    else:
        confirmation = (
            "Thank you for booking with IndiGo!\n"
            "You will receive your PNR via email and WhatsApp shortly.\n\n"
            "Is there anything else I can help you with?\n"
            "- Book a flight ticket\n"
            "- Flight Status\n"
            "- Web Check-in"
        )

    state["assistant_message"] = confirmation
    state["step"] = "SHOW_MENU"
    state["process"] = ""
    state["current_agent"] = "done"
    return state
