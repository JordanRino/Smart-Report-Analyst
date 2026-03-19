"""Streamlit UI configuration and constants."""

# Page configuration
PAGE_TITLE = "Smart Report Analyst"
PAGE_ICON = "📊"

# Chat configuration
MESSAGE_PLACEHOLDER = "Ask me about your data..."
MAX_CHAT_HISTORY = 100  # Limit for performance
RESPONSE_TIMEOUT = 60  # seconds

# Styling constants
SIDEBAR_WIDTH = 300
MAX_MESSAGE_WIDTH = 900

# Session keys for state management
SESSION_CONVERSATION_HISTORY = "conversation_history"
SESSION_AGENT_SESSION_ID = "agent_session_id"
SESSION_SIDEBAR_STATE = "sidebar_state"
SESSION_USER_SETTINGS = "user_settings"

# Message types
MESSAGE_USER = "user"
MESSAGE_ASSISTANT = "assistant"
MESSAGE_ERROR = "error"
MESSAGE_INFO = "info"
