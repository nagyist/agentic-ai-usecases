from utils.prompts.classification import MID_FLOW_INTENT_PROMPT, CONFIRM_INTENT_PROMPT
from utils.llm import call_llm_json
from constants import Step

_INTERCEPTABLE_STEPS = {"SHOW_FLIGHTS", "flight_confirm", Step.DONE, Step.PAYMENT_MODIFY_CONFIRM}

_PAYMENT_WARNING = (
    "Please note that changing your booking details will cancel your current reservation "
    "and the flight prices shown may no longer be available.\n\n"
    "Are you sure you want to make changes?\n"
    "Option - Yes\n"
    "Option - No"
)

_PAYMENT_RESET_FIELDS = (
    "destination_city",
    "departure_airport_code",
    "destination_airport_code",
    "flights",
    "selected_flight",
    "selected_outbound_flight",
    "selected_return_flight",
)


def _classify_modify_intent(user_input: str, step: str) -> str:
    try:
        result = call_llm_json(MID_FLOW_INTENT_PROMPT.format(step=step, user_input=user_input))
        return result.get("intent", "continue")
    except Exception as e:
        print(f"[DEBUG] booking_guardrail mid-flow LLM error: {e}")
        return "continue"


def _classify_confirm_intent(user_input: str) -> str:
    try:
        result = call_llm_json(CONFIRM_INTENT_PROMPT.format(user_input=user_input))
        return result.get("intent", "deny")
    except Exception as e:
        print(f"[DEBUG] booking_guardrail confirm LLM error: {e}")
        return "deny"


def booking_guardrail(state: dict) -> dict:
    """
    Mid-flow intent router. Runs at the entry of the booking subgraph every turn.

    Handles three interception scenarios:
    1. SHOW_FLIGHTS / flight_confirm: redirect modify requests back to slot collection
    2. DONE: show a warning before allowing the user to abandon the payment summary
    3. PAYMENT_MODIFY_CONFIRM: handle the user's yes/no response to the warning
    """
    print(f"\n[DEBUG] booking_guardrail called, step={state.get('step')}")

    step = state.get("step", "")
    if step not in _INTERCEPTABLE_STEPS:
        return state

    user_input = state.get("last_user_input", "")

    # ── Phase 2: handle yes/no response to the payment-modify warning ─────────
    if step == Step.PAYMENT_MODIFY_CONFIRM:
        intent = _classify_confirm_intent(user_input)
        print(f"[DEBUG] booking_guardrail payment_modify_confirm intent: {intent}")
        if intent == "affirm":
            for field in _PAYMENT_RESET_FIELDS:
                state[field] = [] if field in ("flights",) else ({} if "flight" in field else None)
            state["flight_select_attempts"] = 0
            state["awaiting_confirmation"] = False
            state["step"] = Step.COLLECT_SLOTS
            state["current_agent"] = "booking_guardrail"
        else:
            state["step"] = Step.DONE
            state["current_agent"] = "booking_guardrail"
        return state

    # ── Phase 1a: payment-summary step — show warning before modifying ────────
    if step == Step.DONE:
        intent = _classify_modify_intent(user_input, step)
        print(f"[DEBUG] booking_guardrail intent at DONE: {intent}")
        if intent == "modify":
            state["assistant_message"] = _PAYMENT_WARNING
            state["step"] = Step.PAYMENT_MODIFY_CONFIRM
            state["current_agent"] = "booking_guardrail"
        return state

    # ── Phase 1b: mid-flow steps (SHOW_FLIGHTS, flight_confirm) ──────────────
    intent = _classify_modify_intent(user_input, step)
    print(f"[DEBUG] booking_guardrail intent: {intent}")

    if intent == "modify":
        state["flights"] = []
        state["selected_flight"] = {}
        state["flight_select_attempts"] = 0
        state["awaiting_confirmation"] = False
        state["confirmation_step"] = ""
        state["flight_confirmed"] = None
        state["step"] = Step.COLLECT_SLOTS
        state["current_agent"] = "booking_guardrail"

    return state
