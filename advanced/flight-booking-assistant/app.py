import copy
import os
import time
import uuid
import streamlit as st
from datetime import datetime, timezone
from dotenv import load_dotenv
from graph import booking_graph
from utils import llm as llm_module
from config import SESSION_TTL_SECONDS, INITIAL_GREETING
from state import INITIAL_STATE

load_dotenv()

st.set_page_config(
    page_title="Indigo 6ESkai",
    page_icon="✈️",
    layout="wide",
)

st.markdown("""
<style>
    .agent-chip {
        background-color: #000080;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .log-metric {
        font-size: 0.78rem;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)



def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_session_expired(state: dict) -> bool:
    last = state.get("last_active_at")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        delta = datetime.now(timezone.utc) - last_dt
        return delta.total_seconds() > SESSION_TTL_SECONDS
    except Exception:
        return False

_STATE_EXCLUDE = {"messages", "flights", "selected_flight"}


def init_session():
    if "booking_state" not in st.session_state:
        now = _now_iso()
        state = copy.deepcopy(INITIAL_STATE)
        state["session_id"] = str(uuid.uuid4())
        state["started_at"] = now
        state["last_active_at"] = now
        st.session_state.booking_state = state
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": INITIAL_GREETING}]


def _state_snapshot(state: dict) -> dict:
    return {k: v for k, v in state.items() if k not in _STATE_EXCLUDE and v not in (None, "", [], {})}


def render_logs(logs: list, state_snapshot: dict, total_latency_ms: float):
    llm_count = sum(1 for e in logs if e["call_type"] in ("text", "json"))
    node_count = sum(1 for e in logs if e["call_type"] == "node")

    if not logs:
        st.info("No calls logged for this turn.")
    else:
        st.markdown(
            f"**Turn latency:** `{total_latency_ms:.0f} ms` &nbsp;|&nbsp; "
            f"**LLM calls:** `{llm_count}` &nbsp;|&nbsp; **Node calls:** `{node_count}`"
        )
        st.divider()
        for i, entry in enumerate(logs, 1):
            if entry["call_type"] in ("text", "json"):
                label = f"**#{i} LLM** — `{entry['node']}` | {entry['model']} | {entry['total_tokens']} tokens | {entry['latency_ms']} ms"
                with st.expander(label, expanded=False):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Prompt tokens", entry["prompt_tokens"])
                    col2.metric("Completion tokens", entry["completion_tokens"])
                    col3.metric("Total tokens", entry["total_tokens"])
                    col4.metric("Latency (ms)", entry["latency_ms"])

                    with st.expander("Input prompt", expanded=False):
                        st.code(entry["prompt"], language="text")

                    with st.expander("LLM output", expanded=False):
                        st.code(entry["output"], language="text")

            else:  # call_type == "node"
                label = f"**#{i} Node** — `{entry['node']}` | {entry['latency_ms']} ms"
                with st.expander(label, expanded=False):
                    st.metric("Latency (ms)", entry["latency_ms"])
                    st.json(entry["details"])

    st.divider()
    st.markdown("**State snapshot (end of turn)**")
    st.json(state_snapshot or {})


def main():
    st.title("✈️ Indigo 6ESkai — LangGraph Multi-Agent")
    st.caption("Built with LangGraph + OpenAI")

    init_session()

    # Sidebar
    with st.sidebar:
        st.header("Agent Monitor")
        agent = st.session_state.booking_state.get("current_agent", "router")
        st.markdown(f"<span class='agent-chip'>Active: {agent}</span>", unsafe_allow_html=True)

        st.divider()
        st.subheader("Booking Data")
        with st.expander("View current state"):
            display = _state_snapshot(st.session_state.booking_state)
            st.json(display)

        st.divider()
        st.subheader("Flow")
        st.markdown("""
        1. **Router** — intent detection
        2. **Info Collection** — slots (destination, origin, date, passengers)
        3. **Confirmation** — review & confirm details
        4. **Flight Search** — query live DB
        5. **Selection** — pick a flight
        6. **Post-Confirm** — WhatsApp consent, names, email
        7. **Payment** — booking summary
        """)

        if st.button("Reset conversation"):
            st.session_state.clear()
            st.rerun()

    # Chat area — render history
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and "logs" in msg:
                tab_answer, tab_logs = st.tabs(["Assistant", "Logs"])
                with tab_answer:
                    st.write(msg["content"])
                with tab_logs:
                    render_logs(
                        msg["logs"],
                        msg.get("state_snapshot"),
                        msg.get("total_latency_ms", 0),
                    )
            else:
                st.write(msg["content"])

    if st.session_state.booking_state.get("terminated"):
        if st.button("Start a fresh conversation"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    user_input = st.chat_input("Type your message...")

    if user_input:
        # Session expiry check — reset state but preserve channel identity
        if _is_session_expired(st.session_state.booking_state):
            expired_user_id = st.session_state.booking_state.get("user_id", "")
            expired_channel = st.session_state.booking_state.get("channel", "web")
            now = _now_iso()
            fresh = copy.deepcopy(INITIAL_STATE)
            fresh["session_id"] = str(uuid.uuid4())
            fresh["user_id"] = expired_user_id
            fresh["channel"] = expired_channel
            fresh["started_at"] = now
            fresh["last_active_at"] = now
            st.session_state.booking_state = fresh
            st.session_state.chat.append({
                "role": "assistant",
                "content": (
                    "Your session timed out due to inactivity. Starting a fresh booking.\n\n"
                    + INITIAL_GREETING
                ),
            })

        st.session_state.booking_state["last_active_at"] = _now_iso()
        st.session_state.chat.append({"role": "user", "content": user_input})
        st.session_state.booking_state["last_user_input"] = user_input
        st.session_state.booking_state["messages"].append({"role": "user", "content": user_input})
        print(f"\n[DEBUG] User: {user_input}")

        with st.chat_message("user"):
            st.write(user_input)

        try:
            llm_module.reset_logs()
            t0 = time.time()
            with st.spinner("6ESkai is thinking..."):
                result = booking_graph.invoke(st.session_state.booking_state)
            total_latency_ms = (time.time() - t0) * 1000
            run_logs = llm_module.get_logs()
            st.session_state.booking_state = result
        except Exception as e:
            st.error(f"Error: {str(e)}")
            result = st.session_state.booking_state
            run_logs = llm_module.get_logs()
            total_latency_ms = 0

        reply = result.get("assistant_message", "")
        if reply:
            st.session_state.chat.append({
                "role": "assistant",
                "content": reply,
                "logs": run_logs,
                "state_snapshot": _state_snapshot(result),
                "total_latency_ms": total_latency_ms,
            })
            st.session_state.booking_state["messages"].append({"role": "assistant", "content": reply})
            print(f"[DEBUG] AI: {reply}")

        st.rerun()


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set OPENAI_API_KEY in your environment or .env file.")
    else:
        main()
