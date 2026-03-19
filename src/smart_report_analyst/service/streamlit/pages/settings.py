"""Settings page."""

import streamlit as st

from smart_report_analyst.service.streamlit.state import UIState


def settings_page():
    """Render the settings page."""
    st.title("⚙️ Settings")
    st.write("Customize your Smart Report Analyst experience.")

    st.divider()

    # Display Settings
    st.subheader("Display Settings")
    show_timestamps = st.checkbox(
        "Show message timestamps",
        value=UIState.get_setting("show_timestamps", True),
        help="Display the time each message was sent"
    )
    UIState.set_setting("show_timestamps", show_timestamps)

    auto_scroll = st.checkbox(
        "Auto-scroll to latest message",
        value=UIState.get_setting("auto_scroll", True),
        help="Automatically scroll to the most recent message"
    )
    UIState.set_setting("auto_scroll", auto_scroll)

    st.divider()

    # Chat Settings
    st.subheader("Chat Settings")
    st.info(
        "The AI agent maintains conversation history within a session. "
        "Clear your conversation from the sidebar to start fresh."
    )

    if st.button("🗑️ Clear All Conversation History", type="secondary"):
        UIState.clear_conversation()
        st.success("Conversation cleared!")
        st.rerun()

    st.divider()

    # Session Info
    st.subheader("Session Information")
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Session ID",
            UIState.get_agent_session_id()[:16] + "...",
            help="Unique identifier for your current session"
        )

    with col2:
        history = UIState.get_conversation_history()
        st.metric(
            "Messages in Session",
            len(history),
            help="Total messages in current conversation"
        )

    st.divider()

    # About
    st.subheader("About")
    st.write(
        """
    **Smart Report Analyst** — AI-powered data analysis tool
    
    - Built with Streamlit
    - Powered by AWS Bedrock AI Agents
    - Version 0.1.0
    
    For support and feedback, please contact the development team.
    """
    )
