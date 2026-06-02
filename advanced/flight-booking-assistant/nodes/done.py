def done_agent(state: dict) -> dict:
    print(f"\n[DEBUG] done_agent called")
    state["assistant_message"] = (
        "Thank you for booking with IndiGo!\n"
        "You will receive your PNR via email and WhatsApp shortly.\n\n"
        "Is there anything else I can help you with?\n"
        "- Book a flight ticket\n"
        "- Flight Status\n"
        "- Web Check-in"
    )
    state["step"] = "SHOW_MENU"
    state["process"] = ""
    state["current_agent"] = "done"
    return state
