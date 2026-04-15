"""Read Strands FileSessionManager on-disk layout for /history and CopilotKit get_state."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from strands.types.session import SessionMessage

from smart_report_analyst.service.strands.session.manager import (
    _resolved_storage_dir,
    build_strands_session_manager,
)
from smart_report_analyst.service.strands.session.orchestrator_state import get_main_agent_id
from smart_report_analyst.service.strands.session.scoped import composite_session_id

logger = logging.getLogger(__name__)

SESSION_PREFIX = "session_"
AGENT_PREFIX = "agent_"


def _session_dir(storage_root: Path, session_id: str) -> Path:
    return storage_root / f"{SESSION_PREFIX}{session_id}"


def session_exists_on_disk(session_id: str) -> bool:
    root = _resolved_storage_dir()
    session_json = _session_dir(root, session_id) / "session.json"
    return session_json.is_file()


def _list_agent_ids(session_path: Path) -> list[str]:
    agents_dir = session_path / "agents"
    if not agents_dir.is_dir():
        return []
    out: list[str] = []
    for p in agents_dir.iterdir():
        if p.is_dir() and p.name.startswith(AGENT_PREFIX):
            out.append(p.name[len(AGENT_PREFIX) :])
    out.sort()
    return out


def primary_agent_id(session_id: str) -> str | None:
    ids = _list_agent_ids(_session_dir(_resolved_storage_dir(), session_id))
    return ids[0] if ids else None


def list_history_sessions() -> list[dict[str, str]]:
    """
    Sessions as Strands stores them: ``storage/session_<id>/session.json``.
    Returns rows with ``id`` (thread/session id) and ``name`` (short label).
    Sorted by last activity (session.json mtime, fallback dir mtime), newest first.
    """
    storage_dir = _resolved_storage_dir()
    history: list[tuple[dict[str, str], float]] = []

    if not storage_dir.is_dir():
        return []

    for child in storage_dir.iterdir():
        if not child.is_dir() or not child.name.startswith(SESSION_PREFIX):
            continue
        session_id = child.name[len(SESSION_PREFIX) :]
        session_file = child / "session.json"
        if not session_file.is_file():
            continue
        try:
            mtime = session_file.stat().st_mtime
        except OSError:
            mtime = child.stat().st_mtime
        history.append(
            (
                {
                    "id": session_id,
                    "name": f"Analysis {session_id[:8]}...",
                },
                mtime,
            )
        )

    history.sort(key=lambda x: x[1], reverse=True)
    return [h[0] for h in history]


def _flatten_strands_message_for_replay(msg: dict[str, Any]) -> str:
    """Turn Strands Message content blocks into a single string for CopilotKit TextMessage."""
    parts: list[str] = []
    for block in msg.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("text"):
            parts.append(str(block["text"]))
        elif block.get("toolUse"):
            tu = block["toolUse"]
            if isinstance(tu, dict):
                name = tu.get("name", "tool")
                parts.append(f"\n[{name}]\n")
            else:
                parts.append("\n[tool]\n")
        elif block.get("toolResult"):
            parts.append("\n[tool result]\n")
    return "".join(parts).strip()


def session_messages_to_copilot_messages(
    session_messages: list[SessionMessage],
) -> list[dict[str, Any]]:
    """Map persisted SessionMessage list to CopilotKit-style replay messages."""
    out: list[dict[str, Any]] = []
    for sm in session_messages:
        raw = sm.to_message()
        if not isinstance(raw, dict):
            continue
        role = raw.get("role")
        if role not in ("user", "assistant"):
            continue
        content = _flatten_strands_message_for_replay(raw)
        out.append(
            {
                "type": "TextMessage",
                "id": f"strands-msg-{sm.message_id}",
                "createdAt": sm.created_at,
                "role": role,
                "content": content,
            }
        )
    return out


def load_ordered_session_messages(session_id: str, agent_id: str) -> list[SessionMessage]:
    """Load conversation messages via Strands FileSessionManager (ordered by message index)."""
    sm = build_strands_session_manager(session_id)
    return sm.list_messages(session_id, agent_id)


_AGENT_ORCHESTRATOR = "sra_orchestrator_agent"


def _orchestrator_state_dict(thread_id: str, agent_name: str | None) -> dict[str, Any]:
    """Return the ``state`` dict to embed in a get_state response.

    For the orchestrator agent we include ``mainAgentId`` so the frontend can
    hydrate the specialist picker when loading a past thread.
    """
    if agent_name != _AGENT_ORCHESTRATOR:
        return {}
    mid = get_main_agent_id(thread_id)
    return {"mainAgentId": mid} if mid else {}


def get_copilot_state_for_thread(
    thread_id: str,
    *,
    agent_name: str | None = None,
) -> dict[str, Any]:
    """
    Build CopilotKit get_state payload (LangGraphAgent-compatible keys).

    When ``agent_name`` is set, loads the isolated Strands session at
    ``composite_session_id(thread_id, agent_name)`` (per-agent history).

    When omitted, uses legacy layout ``session_<threadId>`` only (pre–multi-agent).

    For the orchestrator agent the ``state`` key includes ``mainAgentId`` from the
    persisted orchestrator state so the frontend can re-hydrate the specialist picker.
    """
    if not thread_id.strip():
        return {
            "threadId": "",
            "threadExists": False,
            "state": {},
            "messages": [],
        }

    root = _resolved_storage_dir()
    agent_state = _orchestrator_state_dict(thread_id, agent_name)

    if agent_name:
        strands_sid = composite_session_id(thread_id, agent_name)
        path = _session_dir(root, strands_sid)
        if not (path / "session.json").is_file():
            return {
                "threadId": thread_id,
                "threadExists": False,
                "state": agent_state,
                "messages": [],
            }
        try:
            session_messages = load_ordered_session_messages(strands_sid, agent_name)
        except Exception:
            logger.exception(
                "load_session_messages_failed session_id=%s agent_id=%s",
                strands_sid,
                agent_name,
            )
            return {
                "threadId": thread_id,
                "threadExists": True,
                "state": agent_state,
                "messages": [],
            }
        messages = session_messages_to_copilot_messages(session_messages)
        return {
            "threadId": thread_id,
            "threadExists": True,
            "state": agent_state,
            "messages": messages,
        }

    path = _session_dir(root, thread_id)
    if not (path / "session.json").is_file():
        return {
            "threadId": thread_id,
            "threadExists": False,
            "state": agent_state,
            "messages": [],
        }

    agent_id = primary_agent_id(thread_id)
    if not agent_id:
        return {
            "threadId": thread_id,
            "threadExists": True,
            "state": agent_state,
            "messages": [],
        }

    try:
        session_messages = load_ordered_session_messages(thread_id, agent_id)
    except Exception:
        logger.exception("load_session_messages_failed session_id=%s agent_id=%s", thread_id, agent_id)
        return {
            "threadId": thread_id,
            "threadExists": True,
            "state": agent_state,
            "messages": [],
        }

    messages = session_messages_to_copilot_messages(session_messages)
    return {
        "threadId": thread_id,
        "threadExists": True,
        "state": agent_state,
        "messages": messages,
    }
