"""Main Chainlit entry point for Smart Report Analyst."""

from __future__ import annotations
import uuid
import chainlit as cl

from smart_report_analyst.ui.chainlit.auth import auth_callback  # noqa
from smart_report_analyst.ui.chainlit.handlers import chat  # noqa
from smart_report_analyst.ui.chainlit.handlers import feedback  # noqa
from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.persistence.mysql.chainlit_data_layer import MySQLDataLayer

settings = get_settings()

data_layer = MySQLDataLayer()

@cl.data_layer
def get_data_layer():
    return data_layer

@cl.on_chat_start
async def on_chat_start():
    # Store session state
    cl.user_session.set("bedrock_session_id", f"br-{uuid.uuid4().hex}")
    cl.user_session.set("chat_history", [])

    await cl.Message(content="Welcome to Smart Report Analyst! How can I assist you today?").send()

@cl.on_chat_resume
async def on_chat_resume(thread):
    """
    Automatically restore a persisted thread for a returning user.
    """
    cl.user_session.set("bedrock_session_id", f"br-{uuid.uuid4().hex}")
    
    await cl.Message(content=f"Resumed: {thread.name or 'New Chat'}").send()