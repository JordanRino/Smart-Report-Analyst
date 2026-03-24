"""Main Chainlit entry point for Smart Report Analyst."""

from __future__ import annotations

import uuid

import chainlit as cl

# VERY IMPORTANT — these imports REGISTER handlers
from smart_report_analyst.ui.chainlit.handlers import chat  # noqa
from smart_report_analyst.ui.chainlit.handlers import feedback  # noqa

@cl.on_chat_start
async def on_chat_start():
    """Initialize a new chat session."""
    cl.user_session.set("session_id", str(uuid.uuid4()))
    cl.user_session.set("last_response", None)
    cl.user_session.set("last_tool_result", None)

    await cl.Message(
        content=(
            "Smart Report Analyst.\n\n"
            "I will run the SQL, summarize the result, and attach a report when the result is tabular."
        )
    ).send()