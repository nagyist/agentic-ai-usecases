from utils.prompts import SYSTEM_PERSONA, CONFIRM_INTENT_PROMPT
from utils.llm import call_llm_json


def _classify_confirm_intent(user_input: str) -> str:
    """Returns 'affirm', 'deny', or 'modify'."""
    prompt = CONFIRM_INTENT_PROMPT.format(system=SYSTEM_PERSONA, user_input=user_input)
    try:
        result = call_llm_json(prompt)
        return result.get("intent", "modify")
    except Exception:
        return "modify"


def confirmation_agent(state: dict) -> dict:
    """Handles pre-search yes/no confirmation after all slots are collected."""
    print(f"\n[DEBUG] confirmation_agent called")

    user_input = state.get("last_user_input", "")
    intent = _classify_confirm_intent(user_input)
    print(f"[DEBUG] confirmation intent: {intent}")

    state["awaiting_confirmation"] = False

    if intent == "affirm":
        state["step"] = "SEARCH_FLIGHTS"
        state["assistant_message"] = "Searching for available flights, please wait..."
    elif intent == "deny":
        for field in ("departure_city", "destination_city", "travel_date", "trip_type", "adults", "children"):
            state[field] = None
        state["step"] = "COLLECT_SLOTS"
        state["assistant_message"] = (
            "No problem! Let us start over.\n"
            "Please tell me your destination city."
        )
    else:
        state["assistant_message"] = (
            "Please reply with Yes to search for flights or No to change your travel details.\n"
            "Option - Yes\n"
            "Option - No"
        )
        state["step"] = "CONFIRM_BOOKING"
        state["awaiting_confirmation"] = True

    state["current_agent"] = "confirmation"
    return state
