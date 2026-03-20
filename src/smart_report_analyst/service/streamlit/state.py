"""Session state management for Streamlit app."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from . import config


class UIState:
    """Manages all session state for the Streamlit app."""

    @staticmethod
    def initialize():
        """Initialize session state with default values."""
        if config.SESSION_CONVERSATION_HISTORY not in st.session_state:
            st.session_state[config.SESSION_CONVERSATION_HISTORY] = []

        if config.SESSION_AGENT_SESSION_ID not in st.session_state:
            st.session_state[config.SESSION_AGENT_SESSION_ID] = str(uuid.uuid4())

        if config.SESSION_USER_SETTINGS not in st.session_state:
            st.session_state[config.SESSION_USER_SETTINGS] = {
                "show_timestamps": True,
                "auto_scroll": True,
            }

    @staticmethod
    def add_message(
        role: str,
        content: str,
        message_type: str = None,
        metadata: Dict[str, Any] = None,
    ):
        """Add a message to conversation history."""
        UIState.initialize()
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "message_type": message_type or config.MESSAGE_ASSISTANT,
            "feedback": None,
            "metadata": metadata or {},
        }
        st.session_state[config.SESSION_CONVERSATION_HISTORY].append(message)

    @staticmethod
    def set_feedback(message_id: str, feedback: str):
        """Set feedback for a specific message."""
        UIState.initialize()
        history = st.session_state[config.SESSION_CONVERSATION_HISTORY]

        for message in history:
            if message.get("id") == message_id:
                message["feedback"] = feedback
                break

    @staticmethod
    def get_message_by_id(message_id: str) -> Dict[str, Any] | None:
        """Retrieve a message by its ID."""
        UIState.initialize()
        history = st.session_state[config.SESSION_CONVERSATION_HISTORY]

        for message in history:
            if message.get("id") == message_id:
                return message

        return None

    @staticmethod
    def get_conversation_history() -> List[Dict[str, Any]]:
        """Get the full conversation history."""
        UIState.initialize()
        return st.session_state[config.SESSION_CONVERSATION_HISTORY]

    @staticmethod
    def clear_conversation():
        """Clear conversation history and reset session."""
        st.session_state[config.SESSION_CONVERSATION_HISTORY] = []
        st.session_state[config.SESSION_AGENT_SESSION_ID] = str(uuid.uuid4())

    @staticmethod
    def get_agent_session_id() -> str:
        """Get the current Bedrock agent session ID."""
        UIState.initialize()
        return st.session_state[config.SESSION_AGENT_SESSION_ID]

    @staticmethod
    def get_setting(setting_name: str, default: Any = None) -> Any:
        """Get a user setting."""
        UIState.initialize()
        settings = st.session_state[config.SESSION_USER_SETTINGS]
        return settings.get(setting_name, default)

    @staticmethod
    def set_setting(setting_name: str, value: Any):
        """Set a user setting."""
        UIState.initialize()
        st.session_state[config.SESSION_USER_SETTINGS][setting_name] = value

    @staticmethod
    def export_conversation() -> str:
        """Export conversation as JSON."""
        history = UIState.get_conversation_history()
        return json.dumps(history, indent=2, default=str)
