"""Main chat page."""

import logging

import streamlit as st

from smart_report_analyst.service.bedrock.agent_manager import BedrockManager
from smart_report_analyst.service.strands.runner import run_strands_turn_sync

from smart_report_analyst.service.streamlit.components import render_chat_input, render_conversation_history, render_export_button
from smart_report_analyst.service.report_generation import generate_pdf
from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.streamlit.state import UIState

logger = logging.getLogger(__name__)
settings = Settings()


bedrock_manager = BedrockManager()


def handle_user_input(user_input: str):
    """Handle user input and get response from agent."""
    # Add user message to history
    UIState.add_message(role="user", content=user_input, message_type="user")

    response = {}

    # Get agent response
    try:
        session_id = UIState.get_agent_session_id()
        
        # Show loading indicator
        with st.spinner("Analyzing your request..."):
            if settings.AGENT_BACKEND == "strands":
                slim_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in UIState.get_conversation_history()
                ]
                response = run_strands_turn_sync(settings, slim_history)
            else:
                response = bedrock_manager.invoke_agent(
                    prompt=user_input,
                    agent_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ID,
                    agent_alias_id=settings.SINGLE_COORDINATOR_BEDROCK_AGENT_ALIAS_ID,
                    session_id=session_id,
                )

        tool_result = response.get("tool_result")

        pdf_buffer = None
        if tool_result and tool_result.get("results"):
            pdf_buffer = generate_pdf(tool_result, user_input)

        # Add assistant response to history
        UIState.add_message(
            role="assistant",
            content=response.get("final_response"),
            message_type="assistant",
                metadata={
                "user_question": response.get("user_question"),
                "tool_result": tool_result,
                "pdf_buffer": pdf_buffer,
            },
        )
        
        
    except Exception as e:
        logger.error(f"Error invoking agent: {e}")
        UIState.add_message(
            role="assistant",
            content=response.get("final_response", "Sorry, something went wrong while processing your request."),
            message_type="assistant",
            metadata={
                "user_question": response.get("user_question"),
            },
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
