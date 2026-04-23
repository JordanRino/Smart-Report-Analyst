"""Build Strands Agent(s): specialists, report builder, and session orchestrator."""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.bedrock.model_manager import build_bedrock_model
from smart_report_analyst.service.strands.agents.prompts import (
    ORCHESTRATOR_INSTRUCTIONS,
    REPORT_BUILDER_INSTRUCTIONS,
    ROUTER_INSTRUCTIONS,
    WLR_REPORTING_INSTRUCTIONS,
    WLR_VERIFICATION_DISCIPLINE,
)
from smart_report_analyst.service.strands.agents.registry import (
    AGENT_ORCHESTRATOR,
    resolve_main_specialist,
)
from smart_report_analyst.service.strands.session import (
    build_strands_session_manager,
)
from smart_report_analyst.service.strands.session.scoped import composite_session_id
from smart_report_analyst.service.strands.conversation import build_strands_conversation_manager
from smart_report_analyst.service.strands.tools import (
    StrandsTurnState,
    build_strands_tools,
    build_report_builder_tools,
)

logger = logging.getLogger(__name__)

# Backward-compatible name for the WLR reporting specialist prompt.
INSTRUCTIONS = WLR_REPORTING_INSTRUCTIONS


def _specialist_system_prompt(agent_id: str) -> str:
    _ = resolve_main_specialist(agent_id)
    return (WLR_REPORTING_INSTRUCTIONS + WLR_VERIFICATION_DISCIPLINE).strip()


def create_specialist_agent(
    turn_state: StrandsTurnState,
    session_manager: Any | None = None,
    conversation_manager: Any | None = None,
    *,
    agent_id: str,
    system_prompt: str | None = None,
    with_tools: bool = True,
) -> Agent:
    """
    Specialist with KB + SQL (same tools for all registered main specialists today).

    ``agent_id`` selects prompt flavor from the registry (currently WLR-style only).
    """
    model = build_bedrock_model()
    tools = build_strands_tools(turn_state) if with_tools else []
    sp = (
        system_prompt.strip()
        if system_prompt is not None
        else _specialist_system_prompt(agent_id)
    )
    tid = (turn_state.thread_id or "").strip()
    if tid:
        sp = (
            f"{sp}\n\n---\nSession context\n"
            f"- Copilot **thread_id** (use this exact value in the `session_metadata.thread_id` column "
            f"when persisting upload-derived metadata): `{tid}`\n"
        )
    meta = resolve_main_specialist(agent_id)
    kwargs: dict[str, Any] = {
        "model": model,
        "tools": tools,
        "system_prompt": sp,
        "callback_handler": None,
        "name": meta.agent_id.replace("-", "_"),
        "description": meta.display_name,
    }
    if session_manager is not None:
        kwargs["session_manager"] = session_manager
        kwargs["messages"] = None
    if conversation_manager is not None:
        kwargs["conversation_manager"] = conversation_manager
    return Agent(**kwargs)


def create_report_builder_agent(
    _turn_state: StrandsTurnState,
    session_manager: Any | None = None,
    conversation_manager: Any | None = None,
) -> Agent:
    """Narrative report writer: no KB/SQL."""
    model = build_bedrock_model()
    kwargs: dict[str, Any] = {
        "model": model,
        "tools": [],
        "system_prompt": REPORT_BUILDER_INSTRUCTIONS.strip(),
        "callback_handler": None,
        "name": "report_builder",
        "description": "Writes reports from a structured brief and supplied text only (no database).",
    }
    if session_manager is not None:
        kwargs["session_manager"] = session_manager
        kwargs["messages"] = None
    if conversation_manager is not None:
        kwargs["conversation_manager"] = conversation_manager
    return Agent(**kwargs)


def create_orchestrator_agent(
    turn_state: StrandsTurnState,
    *,
    main_agent_id: str,
    copilot_thread_id: str,
    orchestrator_session_manager: Any | None,
    orchestrator_conversation_manager: Any | None,
) -> Agent:
    """
    Orchestrator with ``main_specialist`` + ``report_builder`` tools.

    ``turn_state`` is shared with the specialist so ``execute_sql`` results surface on the
    outer Copilot run for AG-UI. The specialist uses ``preserve_context=True`` as_tool when
    a session_manager is present (Strands requirement).
    """
    get_settings()  # fail fast if misconfigured (parity with run_stream validation)

    tid = (copilot_thread_id or "").strip()
    specialist_sid = composite_session_id(tid, f"{AGENT_ORCHESTRATOR}_ms_{main_agent_id}")
    specialist_sm = build_strands_session_manager(specialist_sid)
    specialist_cm = build_strands_conversation_manager()
    specialist = create_specialist_agent(
        turn_state,
        session_manager=specialist_sm,
        conversation_manager=specialist_cm,
        agent_id=main_agent_id,
        with_tools=True,
    )

    builder_sid = composite_session_id(tid, f"{AGENT_ORCHESTRATOR}_report_builder")
    builder_sm = build_strands_session_manager(builder_sid)
    builder_cm = build_strands_conversation_manager()
    builder = create_report_builder_agent(
        turn_state,
        session_manager=builder_sm,
        conversation_manager=builder_cm,
    )

    meta = resolve_main_specialist(main_agent_id)
    main_tool = specialist.as_tool(
        name="main_specialist",
        description=(
            f"Data specialist ({meta.display_name}): KB retrieval, SQL execution, "
            "and cross-checking uploaded reports or metrics against the database. "
            "Pass a clear natural-language task."
        ),
        preserve_context=True,
    )
    builder_tool = builder.as_tool(
        name="report_builder",
        description=(
            "Writes formatted narrative reports from a structured brief and supplied excerpts only. "
            "No database access — confirm numbers with main_specialist first if needed."
        ),
        preserve_context=True,
    )

    report_tools = build_report_builder_tools(turn_state)

    model = build_bedrock_model()
    orch_kwargs: dict[str, Any] = {
        "model": model,
        "tools": [main_tool, builder_tool] + report_tools,
        "system_prompt": ORCHESTRATOR_INSTRUCTIONS.strip(),
        "callback_handler": None,
        "name": AGENT_ORCHESTRATOR,
        "description": "Orchestrates reporting: routes to the selected data specialist and optional report builder.",
    }
    if orchestrator_session_manager is not None:
        orch_kwargs["session_manager"] = orchestrator_session_manager
        orch_kwargs["messages"] = None
    if orchestrator_conversation_manager is not None:
        orch_kwargs["conversation_manager"] = orchestrator_conversation_manager
    return Agent(**orch_kwargs)


def create_strands_agent(
    turn_state: StrandsTurnState,
    session_manager: Any | None = None,
    conversation_manager: Any | None = None,
    *,
    agent_id: str | None = None,
    system_prompt: str | None = None,
    with_tools: bool = True,
) -> Agent:
    """
    Default single-agent factory (backward compatible): WLR specialist when tools are on,
    otherwise router-style agent with ``ROUTER_INSTRUCTIONS``.

    ``agent_id`` selects the specialist prompt variant when ``with_tools=True``.
    """
    model = build_bedrock_model()
    tools = build_strands_tools(turn_state) if with_tools else []
    specialist_key = (agent_id or "wlr_reporting_agent").strip()
    if with_tools:
        sp = (
            system_prompt.strip()
            if system_prompt is not None
            else _specialist_system_prompt(specialist_key)
        )
    else:
        sp = (system_prompt if system_prompt is not None else ROUTER_INSTRUCTIONS).strip()
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
