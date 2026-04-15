"""Persistent orchestrator state: stores session-level config (mainAgentId) per thread.

Separate from FileSessionManager (which owns conversation turns). This module owns
session configuration — specifically which specialist agent is active for a given thread.

Storage: a single JSON file per thread at ``{storage_dir}/orch_{thread_id}.json``.
Writes are atomic (write-to-temp + rename) to avoid partial reads on concurrent access.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from smart_report_analyst.service.strands.session.manager import _resolved_storage_dir

logger = logging.getLogger(__name__)

_ORCH_PREFIX = "orch_"


def _state_path(thread_id: str) -> Path:
    root = _resolved_storage_dir()
    # Sanitise: keep only alphanumeric, dash, and underscore so the file name is safe
    # on all platforms. thread_id is a UUID so this is essentially a no-op in practice.
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in thread_id)
    return root / f"{_ORCH_PREFIX}{safe}.json"


def read_orchestrator_state(thread_id: str) -> dict[str, Any]:
    """Return the persisted orchestrator state for *thread_id*, or ``{}`` if none exists."""
    if not thread_id or not thread_id.strip():
        return {}
    path = _state_path(thread_id.strip())
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.exception("orchestrator_state_read_failed thread_id=%s path=%s", thread_id, path)
        return {}


def write_orchestrator_state(thread_id: str, state: dict[str, Any]) -> None:
    """Atomically persist *state* for *thread_id*.

    Uses write-to-temp-then-rename so readers never see a partial file.
    """
    if not thread_id or not thread_id.strip():
        raise ValueError("thread_id must be a non-empty string")
    if not isinstance(state, dict):
        raise TypeError(f"state must be a dict, got {type(state)!r}")

    path = _state_path(thread_id.strip())
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(state, default=str, ensure_ascii=False, indent=2)
    # Atomic write: temp file in the same directory so os.replace is on the same filesystem.
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".orch_tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup of the temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        logger.exception("orchestrator_state_write_failed thread_id=%s path=%s", thread_id, path)
        raise


def get_main_agent_id(thread_id: str) -> str | None:
    """Convenience: return ``mainAgentId`` from persisted state, or ``None``."""
    state = read_orchestrator_state(thread_id)
    mid = state.get("mainAgentId")
    return mid.strip() if isinstance(mid, str) and mid.strip() else None


def set_main_agent_id(thread_id: str, main_agent_id: str | None) -> None:
    """Convenience: write (or clear) ``mainAgentId`` in the persisted state.

    Passing ``None`` or empty string removes the key so the session reverts to the
    "no specialist chosen" state.
    """
    existing = read_orchestrator_state(thread_id)
    if main_agent_id and main_agent_id.strip():
        existing["mainAgentId"] = main_agent_id.strip()
    else:
        existing.pop("mainAgentId", None)
    write_orchestrator_state(thread_id, existing)
