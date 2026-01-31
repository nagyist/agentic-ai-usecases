import streamlit as st
import os
from dotenv import load_dotenv
from graph import graph, BookingState

load_dotenv()

st.set_page_config(
    page_title="Indigo 6ESkai - LangGraph Agents",
    page_icon="✈️",
    layout="wide"
)

# Styling
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
    .user-msg {
        background-color: #e3f2fd;
        padding: 15px;
        border-radius: 15px;
        margin: 5px 0;
    }
    .assistant-msg {
        background-color: white;
        padding: 15px;
        border-radius: 15px;
        margin: 5px 0;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

def init_state():
    if "booking_state" not in st.session_state:
        st.session_state.booking_state = BookingState(
            messages=[{"role": "assistant", "content": "Hello! I'm 6ESkai, your friendly AI assistant from Indigo.\nHow can I help you with our services today?\n\n1. Book a flight ticket\n2. Flight Status\n3. Web Check in"}],
            current_agent="intent_agent",
            next_step="intent_agent",
            booking_data={},
            search_results=[],
            selected_flight={},
            confirmation_step=""
        )

def main():
    st.title("✈️ Indigo 6ESkai - Pure LangGraph Multi-Agent System")
    st.caption("Built with LangGraph + OpenAI🤖")
    
    init_state()
    
    # Sidebar - Agent Monitor
    with st.sidebar:
        st.header("🎛️ Agent Monitor")
        current = st.session_state.booking_state.get("current_agent", "Starting...")
        st.markdown(f"<span class='agent-chip'>🔵 {current}</span>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📦 Booking Data")
        with st.expander("View State"):
            st.json(st.session_state.booking_state["booking_data"])
        
        st.divider()
        st.subheader("🔄 Graph Flow")
        st.markdown("""
        1. **Intent Agent** 👋
        2. **Info Collection** 📝  
        3. **Flight Search** 🔍
        4. **Selection** ✅
        5. **Confirmation** 📋
        6. **Payment** 💳
        """)
        
        if st.button("🔄 Reset"):
            st.session_state.clear()
            st.rerun()
    
    # Main Chat Area
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state.booking_state["messages"]:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    cols = st.columns([6, 1])
                    with cols[0]:
                        st.write(msg["content"])
                    with cols[1]:
                        agent = st.session_state.booking_state.get("current_agent", "system")
                        st.caption(f"🤖 {agent}")
    
    # Input
    user_input = st.chat_input("Type your message...")
    
    if user_input:
        # Add user message
        st.session_state.booking_state["messages"].append({"role": "user", "content": user_input})
        
        # Process with graph
        try:
            with st.spinner(f"🤖 {st.session_state.booking_state.get('current_agent', 'Agent')} is thinking..."):
                result = graph.invoke(st.session_state.booking_state)
                st.session_state.booking_state = result
        except Exception as e:
            st.error(f"❌ Error processing request: {str(e)}")
            st.session_state.booking_state["messages"].append({
                "role": "assistant",
                "content": f"Sorry, I encountered an error: {str(e)[:200]}"
            })
        
        st.rerun()

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ Please set OPENAI_API_KEY in your environment!")
    else:
        main()