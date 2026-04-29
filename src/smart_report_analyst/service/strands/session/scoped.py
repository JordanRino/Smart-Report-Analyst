"""Composite Strands session ids so each Copilot agent has isolated on-disk state."""

from __future__ import annotations

import re

_AGENT_SAFE = re.compile(r"[^a-zA-Z0-9_-]+")


def composite_session_id(thread_id: str, agent_name: str) -> str:
    """
    One FileSessionManager root per (thread, agent) pair.

    ``thread_id`` is the Copilot thread UUID; ``agent_name`` is the registered
    CopilotKit agent (e.g. ``wlr_reporting_agent``).
    """
    tid = (thread_id or "").strip()
    aid = _AGENT_SAFE.sub("_", (agent_name or "").strip()) or "agent"
    return f"{tid}__{aid}"
