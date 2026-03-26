"""Main Chainlit entry point for Smart Report Analyst."""

from __future__ import annotations
import uuid
import chainlit as cl

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
    """Initialize a new chat session for the authenticated user."""


    current_user = cl.user_session.get("user")  # set by auth_callback
    if not current_user:
        await cl.Message(
            content="You must be logged in to start a chat session."
        ).send()
        return

    user_id = current_user.identifier  


    thread = await data_layer.create_thread(
        user_id=user_id,
        name="New Conversation",
        metadata=None
    )

    cl.user_session.set("session_id", thread.id)  # UUID for this session
    cl.user_session.set("chat_history", [])
    cl.user_session.set("last_response", None)
    cl.user_session.set("last_tool_result", None)


    await cl.Message(
        content=(
            "Smart Report Analyst.\n\n"
            "Ask me anything related to your data, and I will run the SQL, "
            "summarize the result, and attach a report for further reference."
        )
    ).send()