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
        # User wants to modify a specific field — route back to slot collection
        # so info_extractor + city_lookup can apply the change, then re-confirm.
        state["step"] = "COLLECT_SLOTS"
        state["awaiting_confirmation"] = False

    state["current_agent"] = "confirmation"
    return state
