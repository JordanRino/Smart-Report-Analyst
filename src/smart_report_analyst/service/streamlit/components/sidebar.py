"""Sidebar component for navigation and settings."""

import streamlit as st

from smart_report_analyst.service.streamlit import config
from smart_report_analyst.service.streamlit.state import UIState


def render_sidebar():
    """Render the main sidebar with navigation and settings."""
    with st.sidebar:
        st.title(config.PAGE_TITLE)
        st.divider()

        # Navigation
        st.subheader("Navigation")
        page = st.radio(
            "Go to:",
            ["Chat", "Home", "Settings"],
            label_visibility="collapsed",
        )

        st.divider()

        # Chat Settings
        st.subheader("Chat Settings")

        if st.button("🗑️ Clear Conversation", use_container_width=True):
            UIState.clear_conversation()
            st.success("Conversation cleared!")
            st.rerun()

        st.toggle(
            "Show Timestamps",
            value=UIState.get_setting("show_timestamps", True),
            key="show_timestamps",
            on_change=lambda: UIState.set_setting(
                "show_timestamps", st.session_state.show_timestamps
            ),
        )

        st.toggle(
            "Auto Scroll",
            value=UIState.get_setting("auto_scroll", True),
            key="auto_scroll",
            on_change=lambda: UIState.set_setting(
                "auto_scroll", st.session_state.auto_scroll
            ),
        )

        st.divider()

        # Session Info
        st.caption(f"Session ID: `{UIState.get_agent_session_id()[:8]}...`")
        history = UIState.get_conversation_history()
        st.caption(f"Messages: {len(history)}")

        return page
