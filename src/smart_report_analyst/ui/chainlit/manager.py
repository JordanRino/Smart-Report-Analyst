"""Main Chainlit entry point for Smart Report Analyst."""

from __future__ import annotations
import uuid
import chainlit as cl

from smart_report_analyst.ui.chainlit.auth import auth_callback  # noqa
from smart_report_analyst.ui.chainlit.handlers import chat  # noqa
from smart_report_analyst.ui.chainlit.handlers import feedback  # noqa
from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.persistence.mysql.data_layer import MySQLDataLayer
from smart_report_analyst.service.persistence.mysql.data_layer import Pagination, ThreadFilter

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
    current_user = cl.user_session.get("user")

    if not current_user:
        await cl.Message(content="You must be logged in.").send()
        return

    user_id = current_user.identifier

    # Use your list_threads with pagination
    paginated = await data_layer.list_threads(
        pagination=Pagination(limit=50, offset=0),  # get latest 50 chats
        filters=ThreadFilter(user_id=user_id)
    )

    sessions = paginated.items

    actions = []

    # Add previous sessions as actions
    for session in sessions:
        actions.append(
            cl.Action(
                name="resume_chat",
                value=str(session.id),
                label=f"{session.name or 'Chat'} ({session.id})"
            )
        )

    # Add "New Chat" button
    actions.append(
        cl.Action(
            name="new_chat",
            value="new",
            label="➕ New Chat"
        )
    )

    await cl.Message(
        content="Select a conversation or start a new one:",
        actions=actions
    ).send()

@cl.action_callback("new_chat")
async def new_chat(action: cl.Action):
    current_user = cl.user_session.get("user")

    thread = await data_layer.create_thread(
        user_id=current_user.identifier,
        name="New Conversation",
        metadata=None
    )

    cl.user_session.set("thread_id", str(thread.id))
    cl.user_session.set("bedrock_session_id", f"br-{uuid.uuid4().hex}")
    cl.user_session.set("chat_history", [])
    cl.user_session.set("last_response", None)
    cl.user_session.set("last_tool_result", None)

    await cl.Message(content="Started a new conversation.").send()

@cl.on_chat_resume
async def on_chat_resume(thread):
    """
    Automatically restore a persisted thread for a returning user.
    """
    cl.user_session.set("thread_id", str(thread.id))
    cl.user_session.set("bedrock_session_id", f"br-{uuid.uuid4().hex}")

    # Load messages
    messages = await data_layer.get_messages(thread.id)
    history = []

    for msg in messages:
        history.append({
            "role": msg["role"],
            "content": msg["content"]
        })
        await cl.Message(
            content=msg["content"],
            author=msg["role"]
        ).send()

    cl.user_session.set("chat_history", history)

    # Optional: auto-name the chat if empty
    if thread.name is None and history:
        first_msg = history[0]["content"][:50]
        async with data_layer.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE chat_sessions SET name=%s WHERE id=%s",
                    (first_msg, thread.id)
                )

    await cl.Message(
        content=f"Resumed conversation: {thread.name or 'Chat'}"
    ).send()