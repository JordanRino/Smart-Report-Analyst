"""Chat message display components."""

from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from smart_report_analyst.service.streamlit import config
from smart_report_analyst.service.streamlit.state import UIState


def render_chat_message(message: Dict[str, Any]):
    """Render a single chat message."""
    message_id = message.get("id")
    role = message.get("role", "assistant")
    content = message.get("content", "")
    timestamp = message.get("timestamp")
    message_type = message.get("message_type", config.MESSAGE_ASSISTANT)
    feedback = message.get("feedback")

    # Determine avatar and styling
    if role == config.MESSAGE_USER:
        avatar = "👤"
    elif message_type == config.MESSAGE_ERROR:
        avatar = "❌"
    elif message_type == config.MESSAGE_INFO:
        avatar = "ℹ️"
    else:
        avatar = "🤖"

    # Format timestamp if enabled
    time_str = ""
    if UIState.get_setting("show_timestamps") and timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = f" — {dt.strftime('%H:%M:%S')}"
        except:
            pass

    # Display message
    with st.chat_message(role, avatar=avatar):
        st.write(content)
        if time_str:
            st.caption(time_str)

        if role == config.MESSAGE_ASSISTANT and message_type != config.MESSAGE_ERROR:
            # Add feedback buttons for assistant messages
            if feedback is None:
                if st.button("👍", key=f"like_{message['id']}", help = "Mark this response as helpful to help the agent improve its reponses"):
                    message["feedback"] = "like"
                    st.success("Feedback: Like")
                    st.rerun()
            else:
                st.caption("👍 Feedback submitted")


def render_conversation_history():
    """Render the full conversation history."""
    history = UIState.get_conversation_history()

    if not history:
        st.info("Start a conversation by asking a question!")
        return

    for message in history:
        render_chat_message(message)
