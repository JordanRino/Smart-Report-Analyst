"""Main chat page."""

import logging

import streamlit as st

from smart_report_analyst.service.bedrock.manager import BedrockManager

from smart_report_analyst.service.streamlit.components import render_chat_input, render_conversation_history, render_export_button
from smart_report_analyst.service.streamlit.state import UIState

logger = logging.getLogger(__name__)


bedrock_manager = BedrockManager()


def handle_user_input(user_input: str):
    """Handle user input and get response from agent."""
    # Add user message to history
    UIState.add_message(role="user", content=user_input, message_type="user")

    # Get agent response
    try:
        session_id = UIState.get_agent_session_id()
        
        # Show loading indicator
        with st.spinner("Analyzing your request..."):
            response = bedrock_manager.invoke_orchestration(
                prompt=user_input,
                session_id=session_id,
            )
        
        # Add assistant response to history
        UIState.add_message(
            role="assistant",
            content=response,
            message_type="assistant",
        )
        
        
    except Exception as e:
        logger.error(f"Error invoking agent: {e}")
        UIState.add_message(
            role="assistant",
            content=f"Error: {str(e)}",
            message_type="error",
        )
        st.error(f"Failed to get response: {e}")

    st.rerun()


def chat_page():
    """Render the main chat page."""
    st.title("💬 Chat with Smart Report Analyst")
    st.write("Ask me anything about your data. I'll analyze it and provide insights.")

    # Initialize state
    UIState.initialize()

    # Display conversation history
    render_conversation_history()

    st.divider()

    # Chat input
    render_chat_input(on_submit=handle_user_input)

    # Export button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        render_export_button()
