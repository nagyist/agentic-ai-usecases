from datetime import datetime
from utils.prompts import CONVERSATION_DRIVER_PROMPT, SYSTEM_PERSONA
from utils.llm import call_llm


REQUIRED_SLOTS = ["destination_city", "departure_city", "travel_date", "trip_type", "adults"]


def _format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B %Y")
    except Exception:
        return date_str


def conversation_driver_agent(state: dict) -> dict:
    print(f"\n[DEBUG] conversation_driver_agent called")

    missing = [s for s in REQUIRED_SLOTS if not state.get(s)]
    print(f"[DEBUG] missing slots: {missing}")

    if not missing:
        # All slots filled — show summary and ask for confirmation
        children = state.get("children") or 0
        children_text = f", {children} Child" if children > 0 else ""
        date_display = _format_date(state.get("travel_date", ""))

        summary = (
            "Please review your travel details:\n\n"
            f"Departure   : {state.get('departure_city')}\n"
            f"Destination : {state.get('destination_city')}\n"
            f"Travel Date : {date_display}\n"
            f"Trip Type   : {state.get('trip_type')}\n"
            f"Passengers  : {state.get('adults')} Adult(s){children_text}\n\n"
            "To make changes say something like: change destination to Goa, or 2 adults.\n\n"
            "Please confirm to search for flights.\n"
            "Option - Yes\n"
            "Option - No"
        )
        state["assistant_message"] = summary
        state["step"] = "CONFIRM_BOOKING"
        state["current_agent"] = "conversation_driver"
        print(f"[DEBUG] All slots collected, showing confirmation summary")
        return state

    # Ask for next missing slot
    prompt = CONVERSATION_DRIVER_PROMPT.format(system=SYSTEM_PERSONA, state=state)
    output = call_llm(prompt)

    if output.strip() == "READY_FOR_CONFIRMATION":
        # Shouldn't reach here since we checked missing above, but handle gracefully
        state["step"] = "CONFIRM_BOOKING"
    else:
        state["assistant_message"] = output
        state["step"] = "COLLECT_SLOTS"

    state["current_agent"] = "conversation_driver"
    return state
