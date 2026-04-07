"""
In-memory index: CopilotKit thumbs-up sends (thread_id, message_id) only.

We register payloads when emitting successful ``execute_sql`` AG-UI frames, keyed by
assistant ``message_id`` and tool-result ``message_id`` so lookup hits whichever id
the built-in feedback control references.
"""

from __future__ import annotations

import threading
import time
from typing import Any

# Production should swap for Redis + TTL; single-process dev uses this dict.
TTL_SECONDS = 72 * 3600

_lock = threading.Lock()
_store: dict[tuple[str, str], tuple[dict[str, Any], float]] = {}


def _prune_expired() -> None:
    now = time.time()
    dead = [k for k, (_, exp) in _store.items() if exp <= now]
    for k in dead:
        del _store[k]


def register_feedback_snapshot(thread_id: str, message_id: str, payload: dict[str, Any]) -> None:
    """Store a copy of {refined_user_question, executed_sql, to_store} until TTL."""
    if not thread_id or not message_id:
        return
    exp = time.time() + TTL_SECONDS
    snap = {
        "refined_user_question": str(payload.get("refined_user_question") or ""),
        "executed_sql": str(payload.get("executed_sql") or ""),
        "to_store": bool(payload.get("to_store")),
    }
    with _lock:
        _prune_expired()
        _store[(thread_id, message_id)] = (snap, exp)


def pop_feedback_snapshot(thread_id: str, message_id: str) -> dict[str, Any] | None:
    """Remove and return snapshot if present and not expired."""
    if not thread_id or not message_id:
        return None
    with _lock:
        _prune_expired()
        key = (thread_id, message_id)
        ent = _store.pop(key, None)
        if ent is None:
            return None
        snap, exp = ent
        if exp <= time.time():
            return None
        return dict(snap)
