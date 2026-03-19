"""Chat input handling component."""

from typing import Callable, Optional

import streamlit as st

from smart_report_analyst.service.streamlit import config
from smart_report_analyst.service.streamlit.state import UIState


def render_chat_input(
    on_submit: Callable[[str], None],
    placeholder: str = config.MESSAGE_PLACEHOLDER,
) -> Optional[str]:
    """Render chat input area and handle submission.

    Args:
        on_submit: Callback function to handle user input
        placeholder: Placeholder text for input field

    Returns:
        The user input if submitted, None otherwise
    """
    col1, col2 = st.columns([0.85, 0.15])

    with col1:
        user_input = st.text_input(
            label="user_input",
            placeholder=placeholder,
            label_visibility="collapsed",
            key="chat_input",
        )

    with col2:
        submit_button = st.button("Send", use_container_width=True, type="primary")

    if submit_button and user_input.strip():
        on_submit(user_input.strip())
        # Clear input field
        st.session_state["chat_input"] = ""

        # Force UI to refresh immediately
        st.rerun()
        return user_input.strip()

    return None


def render_export_button():
    """Render conversation export button."""

    if st.download_button(
        label="📥 Export Chat",
        data=UIState.export_conversation(),
        file_name="conversation.json",
        mime="application/json",
    ):
        st.success("Conversation exported!")
