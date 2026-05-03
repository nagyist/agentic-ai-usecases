from utils.prompts import WHATSAPP_PROMPT, PASSENGER_PROMPT, EMAIL_PROMPT
from utils.llm import call_llm


def post_confirmation_agent(state: dict) -> dict:
    """
    Multi-step post-selection confirmation:
    flight_confirm → whatsapp_consent → collect_names → collect_email → PAYMENT
    """
    print(f"\n[DEBUG] post_confirmation_agent called, confirmation_step={state.get('confirmation_step')}")

    user_input = state.get("last_user_input", "").lower().strip()
    sub_step = state.get("confirmation_step", "flight_confirm")

    if sub_step == "flight_confirm":
        if "yes" in user_input:
            state["assistant_message"] = call_llm(WHATSAPP_PROMPT)
            state["confirmation_step"] = "whatsapp_consent"
            state["step"] = "whatsapp_consent"
        elif "no" in user_input:
            state["step"] = "SHOW_FLIGHTS"
            state["confirmation_step"] = ""
            state["assistant_message"] = (
                "No problem. Here are the available flights again. Please choose one."
            )
        else:
            state["assistant_message"] = (
                "Please reply Yes to confirm the flight or No to pick a different one.\n"
                "Option - Yes\n"
                "Option - No"
            )

    elif sub_step == "whatsapp_consent":
        state["whatsapp_consent"] = "yes" in user_input
        state["assistant_message"] = call_llm(PASSENGER_PROMPT)
        state["confirmation_step"] = "collect_names"
        state["step"] = "collect_names"

    elif sub_step == "collect_names":
        state["passenger_names"] = state.get("last_user_input", "").strip()
        state["assistant_message"] = call_llm(EMAIL_PROMPT)
        state["confirmation_step"] = "collect_email"
        state["step"] = "collect_email"

    elif sub_step == "collect_email":
        state["email"] = state.get("last_user_input", "").strip()
        state["step"] = "PAYMENT"
        state["confirmation_step"] = "complete"

    state["current_agent"] = "post_confirmation"
    return state
