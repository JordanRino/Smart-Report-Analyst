"""Run Strands conversation turns (streaming and sync)."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.strands.agents import create_strands_agent
from smart_report_analyst.service.strands.tools import StrandsTurnState
from smart_report_analyst.service.strands.utils import split_history_for_turn

logger = logging.getLogger(__name__)


def _validate_strands_settings(settings: Settings) -> None:
    if not settings.BEDROCK_MODEL_ID:
        raise ValueError("BEDROCK_MODEL_ID is required when AGENT_BACKEND=strands")
    if not settings.BEDROCK_KNOWLEDGE_BASE_ID:
        raise ValueError("BEDROCK_KNOWLEDGE_BASE_ID is required when AGENT_BACKEND=strands")


async def async_stream_strands_turn(
    settings: Settings,
    history: list[dict[str, Any]],
) -> AsyncIterator[dict[str, Any]]:
    """
    Async-iterate stream events compatible with Chainlit's chunk / tool_result handling.

    Yields dicts: {"type": "chunk", "data": str} and finally {"type": "tool_result", "data": dict}.
    """
    _validate_strands_settings(settings)
    prior, user_text = split_history_for_turn(history)
    logger.info(
        "strands_stream_turn",
        extra={"prior_turns": len(prior), "user_chars": len(user_text)},
    )
    if not user_text.strip():
        yield {"type": "chunk", "data": "No user message to process."}
        yield {"type": "tool_result", "data": {}}
        return

    turn_state = StrandsTurnState()
    agent = create_strands_agent(settings, turn_state, prior)
    last_result = None
    saw_text = False

    async for event in agent.stream_async(user_text):
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


def run_strands_turn_sync(
    settings: Settings,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Non-streaming turn for Streamlit / CLI."""
    _validate_strands_settings(settings)
    prior, user_text = split_history_for_turn(history)
    logger.info(
        "strands_complete_turn",
        extra={"prior_turns": len(prior), "user_chars": len(user_text)},
    )
    if not user_text.strip():
        return {
            "final_response": "No user message to process.",
            "user_question": "",
            "tool_result": {},
        }

    turn_state = StrandsTurnState()
    agent = create_strands_agent(settings, turn_state, prior)
    result = agent(user_text)
    final_text = str(result).strip()
    return {
        "final_response": final_text,
        "user_question": user_text,
        "tool_result": turn_state.last_tool_result or {},
    }
