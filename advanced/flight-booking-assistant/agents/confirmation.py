def confirmation_agent(state: dict) -> dict:
    """Handles pre-search yes/no confirmation after all slots are collected."""
    print(f"\n[DEBUG] confirmation_agent called")

    user_input = state.get("last_user_input", "").lower().strip()

    if "yes" in user_input:
        state["step"] = "SEARCH_FLIGHTS"
        state["assistant_message"] = "Searching for available flights, please wait..."
    elif "no" in user_input:
        # Reset slot data so user can start fresh
        for field in ("departure_city", "destination_city", "travel_date", "trip_type", "adults", "children"):
            state[field] = None
        state["step"] = "COLLECT_SLOTS"
        state["assistant_message"] = (
            "No problem! Let us start over.\n"
            "Please tell me your destination city."
        )
    else:
        # Unclear reply — re-ask
        state["assistant_message"] = (
            "Please reply with Yes to search for flights or No to change your travel details.\n"
            "Option - Yes\n"
            "Option - No"
        )
        state["step"] = "CONFIRM_BOOKING"

    state["current_agent"] = "confirmation"
    return state
