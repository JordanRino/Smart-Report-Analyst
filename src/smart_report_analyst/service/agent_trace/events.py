"""Canonical trace events emitted during an agent run (backend-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TraceKind(str, Enum):
    """High-level trace categories."""

    STEP_STARTED = "step_started"
    STEP_FINISHED = "step_finished"
    REASONING_LINE = "reasoning_line"
    CUSTOM = "custom"
    # Bedrock Converse ``reasoningContent`` deltas (Strands ``ReasoningTextStreamEvent``).
    MODEL_REASONING_DELTA = "model_reasoning_delta"


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """
    One logical trace unit. Mapped to AG-UI STEP_*, REASONING_MESSAGE_CONTENT, CUSTOM,
    or (for ``MODEL_REASONING_DELTA``) the same reasoning channel as ``REASONING_LINE``.

    ``schema_version`` bumps when payload keys change for CUSTOM consumers.
    """

    run_id: str
    thread_id: str
    agent_name: str
    step_id: int
    ts_ms: int
    kind: TraceKind
    payload: dict[str, Any] = field(default_factory=dict)
