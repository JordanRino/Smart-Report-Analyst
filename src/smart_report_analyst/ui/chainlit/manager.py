"""Main Chainlit entry point for Smart Report Analyst."""

from __future__ import annotations

import uuid
import chainlit as cl

# VERY IMPORTANT — these imports REGISTER handlers
from smart_report_analyst.ui.chainlit.handlers import chat  # noqa
from smart_report_analyst.ui.chainlit.handlers import feedback  # noqa
from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.persistence.mysql.data_layer import MySQLDataLayer

settings = Settings()

data_layer = MySQLDataLayer(
    host=settings.MYSQL_HOST,
    user=settings.MYSQL_USER,
    password=settings.MYSQL_PASSWORD,
    db=settings.MYSQL_DB,
    port=settings.MYSQL_PORT,
)


@cl.on_chat_start
async def on_chat_start():
    """Initialize a new chat session."""

    session_id = str(uuid.uuid4())  # always generate a session id

    thread = await data_layer.create_thread(
        user_id=session_id,
        name="New Conversation",
    )

    cl.user_session.set("session_id", thread.id)
    cl.user_session.set("chat_history", [])
    cl.user_session.set("last_response", None)
    cl.user_session.set("last_tool_result", None)

    await cl.Message(
        content=(
            "Smart Report Analyst.\n\n"
            "Ask me anything related to your data, and I will run the SQL, summarize the result, and attach a report for further reference."
        )
    ).send()