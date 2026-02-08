"""Streamlit UI for the clinic booking chatbot."""

import streamlit as st
from agents.booking_agent import create_initial_state, process_message
from data.db import init_db


def initialize_session():
    """Initialize session state."""
    if "state" not in st.session_state:
        st.session_state.state = create_initial_state()
    if "initialized" not in st.session_state:
        st.session_state.initialized = False


def display_chat_history():
    """Display the chat history."""
    for message in st.session_state.state["messages"]:
        if message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(message["content"])
        else:
            with st.chat_message("user"):
                st.markdown(message["content"])


def display_options():
    """Display clickable options as buttons."""
    options = st.session_state.state.get("available_options", [])
    
    if options and st.session_state.state["stage"] not in ["completed", "cancelled"]:
        st.markdown("---")
        st.markdown("**Click an option:**")
        
        # Create columns for buttons
        cols = st.columns(min(len(options), 3))
        
        for idx, option in enumerate(options):
            col_idx = idx % 3
            with cols[col_idx]:
                if st.button(option, key=f"btn_{option}_{idx}", use_container_width=True):
                    handle_user_input(option)


def handle_user_input(user_input: str):
    """Handle user input and process through agent."""
    # Process the message
    st.session_state.state = process_message(st.session_state.state, user_input)
    
    # Rerun to update UI
    st.rerun()


def run_chat_ui():
    """Run the chat UI."""
    # Page config
    st.set_page_config(
        page_title="CarePlus Clinic - Book Appointment",
        page_icon="🏥",
        layout="centered"
    )
    
    # Initialize database
    init_db()
    
    # Initialize session
    initialize_session()
    
    # Header
    st.title("🏥 CarePlus Clinic")
    st.markdown("*Book your doctor appointment easily*")
    st.markdown("---")
    
    # Send initial greeting if not initialized
    if not st.session_state.initialized:
        st.session_state.state = process_message(st.session_state.state, "Hi")
        st.session_state.initialized = True
        st.rerun()
    
    # Display chat history
    display_chat_history()
    
    # Display clickable options
    display_options()
    
    # Chat input (only show if not completed)
    if st.session_state.state["stage"] not in ["completed", "cancelled"]:
        if prompt := st.chat_input("Type your message here..."):
            handle_user_input(prompt)
    else:
        # Show restart button after completion
        st.markdown("---")
        if st.button("🔄 Start New Booking", use_container_width=True):
            st.session_state.state = create_initial_state()
            st.session_state.initialized = False
            st.rerun()