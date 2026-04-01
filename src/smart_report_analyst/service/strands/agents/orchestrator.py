"""Build Strands Agent with SRA system prompt and tools."""

from __future__ import annotations

import logging
from pathlib import Path

from strands import Agent

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.bedrock.model_manager import build_bedrock_model
from smart_report_analyst.service.strands.tools import StrandsTurnState, build_strands_tools
from smart_report_analyst.service.strands.utils import chainlit_history_to_strands_messages

logger = logging.getLogger(__name__)

STRANDS_TOOL_ADDENDUM = """

## Strands tool contract (this deployment)
- Call **retrieve_kb_context** with a focused search string when you need schema metadata or similar historical SQL from the knowledge base.
- Call **execute_sql** to run SQL. Arguments must be exactly:
  - **query**: the SQL string.
  - **user_refined_question**: concise analytical question text.
  - **to_store**: boolean; false only when an identical question+SQL pair already exists in KB context.
- Always summarize query results for the user. Put executed SQL in a Markdown ```sql fenced block.
"""


def _repo_root() -> Path:
    # service/strands/agents/orchestrator.py -> parents to repo root
    return Path(__file__).resolve().parents[5]


def load_strands_system_prompt() -> str:
    """Load the all-in-one coordinator instructions from repo `agent_prompts` (first section)."""
    path = _repo_root() / "agent_prompts"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("agent_prompts not found at %s; using minimal fallback prompt", path)
        return _FALLBACK_SYSTEM_PROMPT

    marker = "\n\nCOORDINATOR AGENT for Smart Report Analyst"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text.strip() + STRANDS_TOOL_ADDENDUM


_FALLBACK_SYSTEM_PROMPT = """You are the Smart Report Analyst coordinator for SBA loan analytics.
Use retrieve_kb_context for schema and historical SQL patterns, then execute_sql with query,
user_refined_question, and to_store. Summarize results clearly and show SQL in a markdown sql block.
""" + STRANDS_TOOL_ADDENDUM


def create_strands_agent(
    settings: Settings,
    turn_state: StrandsTurnState,
    prior_messages: list[dict],
) -> Agent:
    """Create a fresh Agent for one turn (prior conversation + new user message via stream_async)."""
    model = build_bedrock_model(settings)
    tools = build_strands_tools(settings, turn_state)
    system_prompt = load_strands_system_prompt()
    strands_messages = chainlit_history_to_strands_messages(prior_messages)
    return Agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        messages=strands_messages,
        callback_handler=None,
    )
