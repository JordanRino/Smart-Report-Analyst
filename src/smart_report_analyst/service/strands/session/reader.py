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


def logical_thread_id(stored_session_id: str) -> str:
    """
    Copilot ``threadId`` for history grouping.

    Strands composite keys look like ``<thread_uuid>__<agent_suffix>`` (see
    :func:`~smart_report_analyst.service.strands.session.scoped.composite_session_id`).
    Multiple on-disk session dirs can share one logical thread; the sidebar shows
    one row per thread. Legacy dirs with no ``__`` use the full id as the thread.
    """
    s = (stored_session_id or "").strip()
    if "__" not in s:
        return s
    head, _tail = s.split("__", 1)
    return head if head else s


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
    One sidebar row per Copilot thread.

    Strands may create several ``storage/session_<composite_id>/`` trees per thread
    (orchestrator, specialist-as-tool, report builder). We group by
    :func:`logical_thread_id`, use the newest ``session.json`` mtime in each group
    for ordering, and return ``id`` = the logical Copilot ``threadId`` (not the
    composite storage key).
    """
    storage_dir = _resolved_storage_dir()
    if not storage_dir.is_dir():
        return []

    # logical_thread_id -> max mtime across all composite session dirs for that thread
    last_activity: dict[str, float] = {}

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

        logical = logical_thread_id(session_id)
        prev = last_activity.get(logical)
        if prev is None or mtime > prev:
            last_activity[logical] = mtime

    ordered = sorted(last_activity.items(), key=lambda x: x[1], reverse=True)
    return [
        {
            "id": logical,
            "name": f"Analysis {logical[:8]}...",
        }
        for logical, _mtime in ordered
    ]


_GENERATE_REPORT_PDF_TOOL = "generate_report_pdf"


def _extract_report_id_from_tool_result(text: str) -> str | None:
    """Parse ``report_id=<uuid>`` from the tool's return string."""
    import re
    m = re.search(r"report_id=([0-9a-f-]{36})", text)
    return m.group(1) if m else None


def _visible_replay_text(msg: dict[str, Any]) -> str:
    """Human-visible text for history replay: ``text`` blocks only, optional attachment hint.

    Omits ``toolUse`` / ``toolResult`` (no ``[main_specialist]``, ``[tool result]``, etc.).
    Preserves newlines inside each ``text`` block (markdown tables, lists). Multiple
    ``text`` blocks in one message are joined with blank lines.
    """
    parts: list[str] = []
    for block in msg.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("text"):
            parts.append(str(block["text"]).strip())
        elif block.get("document"):
            parts.append("[attachment]")
    raw = "\n\n".join(p for p in parts if p) if parts else ""
    return raw.strip()


def _build_deliver_report_action_message(
    report_id: str,
    title: str,
    base_id: str,
    created_at: str,
) -> dict[str, Any]:
    """Build a CopilotKit ActionExecutionMessage for deliver_report replay."""
    import json as _json
    return {
        "type": "ActionExecutionMessage",
        "id": f"{base_id}-deliver-report",
        "createdAt": created_at,
        "role": "assistant",
        "name": "deliver_report",
        "arguments": _json.dumps({"report_id": report_id, "title": title}),
        "status": "complete",
    }


def session_messages_to_copilot_messages(
    session_messages: list[SessionMessage],
) -> list[dict[str, Any]]:
    """Map persisted SessionMessage list to CopilotKit-style replay messages.

    Q&A-style replay: only human-visible ``text`` (and an ``[attachment]`` hint for
    document blocks). Drops tool-only turns (no ``[tool result]``, ``[main_specialist]``).

    When ``generate_report_pdf`` completes, we still append ``deliver_report``
    ``ActionExecutionMessage`` after the resolving user message so report cards replay.
    """
    pending_report_tool_ids: dict[str, tuple[str, int]] = {}

    out: list[dict[str, Any]] = []
    for sm in session_messages:
        raw = sm.to_message()
        if not isinstance(raw, dict):
            continue
        role = raw.get("role")
        if role not in ("user", "assistant"):
            continue

        content_blocks = raw.get("content") or []
        msg_id = f"strands-msg-{sm.message_id}"

        if role == "assistant":
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                tu = block.get("toolUse")
                if isinstance(tu, dict) and tu.get("name") == _GENERATE_REPORT_PDF_TOOL:
                    tool_use_id = tu.get("toolUseId", "")
                    title = str(tu.get("input", {}).get("title", "Report"))
                    if tool_use_id:
                        pending_report_tool_ids[tool_use_id] = (title, len(out))

            visible = _visible_replay_text(raw)
            if visible:
                out.append(
                    {
                        "type": "TextMessage",
                        "id": msg_id,
                        "createdAt": sm.created_at,
                        "role": role,
                        "content": visible,
                    }
                )

        elif role == "user":
            deliver_report_msgs: list[dict[str, Any]] = []
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                tr = block.get("toolResult")
                if not isinstance(tr, dict):
                    continue
                tool_use_id = tr.get("toolUseId", "")
                if tool_use_id not in pending_report_tool_ids:
                    continue
                tr_content = tr.get("content") or []
                result_text = ""
                for rc in tr_content:
                    if isinstance(rc, dict) and rc.get("text"):
                        result_text += rc["text"]
                report_id = _extract_report_id_from_tool_result(result_text)
                if report_id:
                    title, _ = pending_report_tool_ids.pop(tool_use_id)
                    deliver_report_msgs.append(
                        _build_deliver_report_action_message(
                            report_id=report_id,
                            title=title,
                            base_id=msg_id,
                            created_at=sm.created_at,
                        )
                    )

            visible = _visible_replay_text(raw)
            if visible:
                out.append(
                    {
                        "type": "TextMessage",
                        "id": msg_id,
                        "createdAt": sm.created_at,
                        "role": role,
                        "content": visible,
                    }
                )
            out.extend(deliver_report_msgs)

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
        # Strands stores messages under ``agents/agent_<id>/messages`` where ``id`` is often
        # ``default`` (not the CopilotKit registration name). Prefer the on-disk agent id.
        strands_agent_id = primary_agent_id(strands_sid) or agent_name
        try:
            session_messages = load_ordered_session_messages(strands_sid, strands_agent_id)
        except Exception:
            logger.exception(
                "load_session_messages_failed session_id=%s agent_id=%s",
                strands_sid,
                strands_agent_id,
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
