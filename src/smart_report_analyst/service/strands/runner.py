"""Run Strands conversation turns (streaming and sync)."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.strands.agents import create_strands_agent
from smart_report_analyst.service.strands.tools import StrandsTurnState
from smart_report_analyst.service.strands.utils import split_history_for_turn
from smart_report_analyst.service.strands.session import build_strands_session_manager
from smart_report_analyst.service.strands.conversation import (build_strands_conversation_manager,)
from smart_report_analyst.config.settings import get_settings


logger = logging.getLogger(__name__)


def _validate_strands_settings() -> None:
    settings = get_settings()
    if not settings.BEDROCK_MODEL_ID:
        raise ValueError("BEDROCK_MODEL_ID is required when AGENT_BACKEND=strands")
    if not settings.BEDROCK_KNOWLEDGE_BASE_ID:
        raise ValueError("BEDROCK_KNOWLEDGE_BASE_ID is required when AGENT_BACKEND=strands")


async def run_stream(
    user_message: str,
    session_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """
    Async-iterate stream events compatible with Chainlit's chunk / tool_result handling.

    Yields dicts: {"type": "chunk", "data": str} and finally {"type": "tool_result", "data": dict}.
    """
    _validate_strands_settings()
    logger.info(
        "strands_stream_turn",
        extra={
            "user_chars": len(user_message),
        },
    )
    if not user_message.strip():
        yield {"type": "chunk", "data": "No user message to process."}
        yield {"type": "tool_result", "data": {}}
        return

    turn_state = StrandsTurnState()
    sm = build_strands_session_manager(session_id)
    cm = build_strands_conversation_manager()
    agent = create_strands_agent(
        turn_state,
        session_manager=sm,
        conversation_manager=cm,
    )

    last_result = None
    saw_text = False

    async for event in agent.stream_async(user_message):
        if not isinstance(event, dict):
            continue
        data = event.get("data")
        if isinstance(data, str) and data:
            saw_text = True
            yield {"type": "chunk", "data": data}
        if "result" in event:
            last_result = event.get("result")

    if not saw_text and last_result is not None:
        fallback = str(last_result).strip()
        if fallback:
            yield {"type": "chunk", "data": fallback}

    yield {"type": "tool_result", "data": turn_state.last_tool_result or {}}


def run_sync(
    user_message: str,
    session_id: str,
) -> dict[str, Any]:
    """Non-streaming turn for Streamlit / CLI."""

    _validate_strands_settings()
    logger.info(
        "strands_complete_turn",
        extra={
            "user_chars": len(user_message),
        },
    )
    if not user_message.strip():
        return {
            "final_response": "No user message to process.",
            "user_question": "",
            "tool_result": {},
        }

    turn_state = StrandsTurnState()

    sm = build_strands_session_manager(session_id)
    cm = build_strands_conversation_manager()
    agent = create_strands_agent(
        turn_state,
        session_manager=sm,
        conversation_manager=cm,
    )

    result = agent(user_message)
    final_text = str(result).strip()
    return {
        "final_response": final_text,
        "user_question": user_message,
        "tool_result": turn_state.last_tool_result or {},
    }
