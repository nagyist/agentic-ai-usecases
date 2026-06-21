import json
from utils.prompts.conversation import ROUTING_PROMPT, OUT_OF_SCOPE_PROMPT, SYSTEM_PERSONA
from utils.formatting import format_history
from utils.llm import call_llm

_PROCESS_LABELS = {
    "book_flight":  "flight booking",
    "web_checkin":  "web check-in",
    "flight_status": "flight status",
}


def route(state: dict) -> dict:
    print(f"\n[DEBUG] route called, step={state.get('step')}")

    user_input = state.get("last_user_input", "").strip()
    history = format_history(state.get("messages", []))
    state["current_agent"] = "router"

    # ── Exit command ─────────────────────────────────────────────────────────
    if user_input.lower() == "exit":
        state["process"] = ""
        state["pnr"] = ""
        state["step"] = "SHOW_MENU"
        state["intent"] = "greeting"
        state["assistant_message"] = _default_menu()
        return state

    # ── Process-switching guard ───────────────────────────────────────────────
    current_process = state.get("process", "")
    if current_process:
        prompt = ROUTING_PROMPT.format(
            system=SYSTEM_PERSONA,
            conversation_history=history,
            user_input=user_input,
        )
        raw = call_llm(prompt)
        new_intent = _parse_intent(raw)
        print(f"[DEBUG] guard check — current_process={current_process}, new_intent={new_intent}")

        # If user is trying to start a different process, block it
        if new_intent in ("book_flight", "web_checkin", "flight_status") and new_intent != current_process:
            label = _PROCESS_LABELS.get(current_process, current_process)
            state["assistant_message"] = (
                f"You are already in {label} process. "
                "Please type 'exit' to leave the current process and start a new one."
            )
            state["step"] = "COLLECT_PNR" if current_process in ("web_checkin", "flight_status") else "COLLECT_SLOTS"
            return state

        intent = new_intent
    else:
        prompt = ROUTING_PROMPT.format(
            system=SYSTEM_PERSONA,
            conversation_history=history,
            user_input=user_input,
        )
        raw = call_llm(prompt)
        print(f"[DEBUG] router LLM raw: {raw[:120]}")
        intent = _parse_intent(raw)

    print(f"[DEBUG] resolved intent: {intent}")

    if intent == "book_flight":
        state["intent"] = "book_flight"
        state["process"] = "book_flight"
        state["step"] = "COLLECT_SLOTS"
        state["assistant_message"] = (
            "Sure! Let me help you book a flight.\n"
            "Please tell me your destination city."
        )
        return state

    if intent == "web_checkin":
        state["intent"] = "web_checkin"
        state["process"] = "web_checkin"
        state["step"] = "COLLECT_PNR"
        return state

    if intent == "flight_status":
        state["intent"] = "flight_status"
        state["process"] = "flight_status"
        state["step"] = "COLLECT_PNR"
        return state

    if intent == "out_of_scope":
        oos_prompt = OUT_OF_SCOPE_PROMPT.format(
            system=SYSTEM_PERSONA, user_input=user_input
        )
        state["assistant_message"] = call_llm(oos_prompt)
        state["step"] = "SHOW_MENU"
        state["intent"] = "out_of_scope"
        return state

    # intent == "greeting" (or fallback)
    try:
        parsed = json.loads(raw)
        reply = parsed.get("reply", "")
    except (json.JSONDecodeError, AttributeError):
        reply = ""

    state["assistant_message"] = reply or _default_menu()
    state["step"] = "SHOW_MENU"
    state["intent"] = "greeting"
    return state


def _parse_intent(raw: str) -> str:
    try:
        parsed = json.loads(raw.strip())
        return parsed.get("intent", "greeting")
    except (json.JSONDecodeError, AttributeError):
        return "greeting"


def _default_menu() -> str:
    return (
        "Hello! I am 6ESkai, your IndiGo virtual booking assistant.\n"
        "How can I help you today?\n"
        "- Book a flight ticket\n"
        "- Flight Status\n"
        "- Web Check-in"
    )
