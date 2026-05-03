import json
from utils.prompts import GREETING_PROMPT, SYSTEM_PERSONA
from utils.llm import call_llm


def greeting_agent(state: dict) -> dict:
    print(f"\n[DEBUG] greeting_agent called, step={state.get('step')}")

    user_input = state.get("last_user_input", "")

    prompt = GREETING_PROMPT.format(system=SYSTEM_PERSONA, user_input=user_input)
    output = call_llm(prompt)
    print(f"[DEBUG] greeting LLM output: {output[:80]}")

    # LLM returns JSON when user wants to book, plain text otherwise
    try:
        parsed = json.loads(output)
        if parsed.get("intent") == "book_flight":
            state["intent"] = "book_flight"
            state["step"] = "COLLECT_SLOTS"
            state["assistant_message"] = (
                "Great! Let me help you book a flight.\n"
                "Please tell me your destination city."
            )
            state["current_agent"] = "greeting"
            return state
    except (json.JSONDecodeError, AttributeError):
        pass

    state["assistant_message"] = output
    state["step"] = "SHOW_MENU"
    state["current_agent"] = "greeting"
    return state
