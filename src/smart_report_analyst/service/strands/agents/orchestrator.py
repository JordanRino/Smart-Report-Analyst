"""Build Strands Agent with configurable system prompt (per CopilotKit agent)."""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent

from smart_report_analyst.service.bedrock.model_manager import build_bedrock_model
from smart_report_analyst.service.strands.agents.prompts import WLR_REPORTING_INSTRUCTIONS
from smart_report_analyst.service.strands.tools import StrandsTurnState, build_strands_tools

logger = logging.getLogger(__name__)

# Backward-compatible name for the WLR reporting specialist prompt.
INSTRUCTIONS = WLR_REPORTING_INSTRUCTIONS


def create_strands_agent(
    turn_state: StrandsTurnState,
    session_manager: Any | None = None,
    conversation_manager: Any | None = None,
    *,
    system_prompt: str | None = None,
    with_tools: bool = True,
) -> Agent:
    """
    Create an Agent for one turn.

    When ``session_manager`` is set (STRANDS_SESSION_PERSISTENCE), history is loaded from the
    session store.

    ``system_prompt`` defaults to the WLR reporting specialist instructions when omitted.
    Set ``with_tools=False`` for router / front-door agents that must not call KB or SQL.
    """
    model = build_bedrock_model()
    tools = build_strands_tools(turn_state) if with_tools else []
    sp = (system_prompt if system_prompt is not None else WLR_REPORTING_INSTRUCTIONS).strip()
    kwargs: dict[str, Any] = {
        "model": model,
        "tools": tools,
        "system_prompt": sp,
        "callback_handler": None,
    }
    if session_manager is not None:
        kwargs["session_manager"] = session_manager
        kwargs["messages"] = None
    if conversation_manager is not None:
        kwargs["conversation_manager"] = conversation_manager
    return Agent(**kwargs)
