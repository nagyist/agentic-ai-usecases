import os
import streamlit as st
from dotenv import load_dotenv
from graph import booking_graph

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
</style>
""", unsafe_allow_html=True)


INITIAL_STATE = {
    "messages": [],
    "last_user_input": "",
    "assistant_message": "",
    "step": "GREETING",
    "current_agent": "greeting",
    "intent": None,
    "departure_city": None,
    "destination_city": None,
    "travel_date": None,
    "trip_type": None,
    "adults": None,
    "children": None,
    "confirmation_step": "",
    "whatsapp_consent": None,
    "passenger_names": "",
    "email": "",
    "flights": [],
    "selected_flight": {},
}

INITIAL_GREETING = (
    "Hello! I am 6ESkai, your friendly AI assistant from Indigo.\n"
    "How can I help you with our services today?\n\n"
    "- Book a flight ticket\n"
    "- Flight Status\n"
    "- Web Check in"
)


def init_session():
    if "booking_state" not in st.session_state:
        st.session_state.booking_state = dict(INITIAL_STATE)
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": INITIAL_GREETING}]


def main():
    st.title("✈️ Indigo 6ESkai — LangGraph Multi-Agent")
    st.caption("Built with LangGraph + OpenAI")

    init_session()

    # Sidebar
    with st.sidebar:
        st.header("Agent Monitor")
        agent = st.session_state.booking_state.get("current_agent", "greeting")
        st.markdown(f"<span class='agent-chip'>Active: {agent}</span>", unsafe_allow_html=True)

        st.divider()
        st.subheader("Booking Data")
        with st.expander("View current state"):
            display = {
                k: v for k, v in st.session_state.booking_state.items()
                if k not in ("messages", "flights", "selected_flight")
                and v not in (None, "", [], {})
            }
            st.json(display)

        st.divider()
        st.subheader("Flow")
        st.markdown("""
        1. **Greeting** — intent detection
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

    # Chat area
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Type your message...")

    if user_input:
        st.session_state.chat.append({"role": "user", "content": user_input})
        st.session_state.booking_state["last_user_input"] = user_input

        try:
            with st.spinner(f"6ESkai is thinking..."):
                result = booking_graph.invoke(st.session_state.booking_state)
                st.session_state.booking_state = result
        except Exception as e:
            st.error(f"Error: {str(e)}")
            result = st.session_state.booking_state

        reply = result.get("assistant_message", "")
        if reply:
            st.session_state.chat.append({"role": "assistant", "content": reply})

        st.rerun()


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set OPENAI_API_KEY in your environment or .env file.")
    else:
        main()
