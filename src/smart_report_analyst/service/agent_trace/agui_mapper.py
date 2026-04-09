"""Map :class:`TraceEvent` to AG-UI SSE frame strings."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from smart_report_analyst.integrations import agui_stream
from smart_report_analyst.service.agent_trace.events import TraceEvent, TraceKind

# CopilotKit / AG-UI: activity stream for server-side tool progress (not REASONING_*).
DEFAULT_TOOL_TRACE_ACTIVITY_TYPE = "smart_report_analyst.tool_trace"


@dataclass
class ToolTraceActivityState:
    """Turn-scoped state for ``ACTIVITY_SNAPSHOT`` with ``replace=True``."""

    lines: list[str] = field(default_factory=list)
    open_steps: list[str] = field(default_factory=list)
    timings: list[dict[str, Any]] = field(default_factory=list)

    def to_content(self) -> dict[str, Any]:
        return {
            "lines": list(self.lines),
            "openSteps": list(self.open_steps),
            "timings": list(self.timings),
        }

    def apply(self, ev: TraceEvent) -> None:
        if ev.kind == TraceKind.STEP_STARTED:
            name = str(ev.payload.get("step_name") or "step").strip()
            if name and name not in self.open_steps:
                self.open_steps.append(name)
        elif ev.kind == TraceKind.STEP_FINISHED:
            name = str(ev.payload.get("step_name") or "step").strip()
            if name in self.open_steps:
                self.open_steps.remove(name)
        elif ev.kind == TraceKind.REASONING_LINE:
            text = str(ev.payload.get("text") or "").rstrip()
            if text:
                self.lines.append(text)
        elif ev.kind == TraceKind.CUSTOM:
            name = str(ev.payload.get("name") or "")
            value = ev.payload.get("value")
            if name == "tool_timing_ms" and isinstance(value, dict):
                self.timings.append(dict(value))
        elif ev.kind == TraceKind.MODEL_REASONING_DELTA:
            text = str(ev.payload.get("text") or "").strip()
            if text:
                self.lines.append(text)


def trace_event_to_activity_snapshot_frame(
    ev: TraceEvent,
    *,
    state: ToolTraceActivityState,
    message_id: str,
    activity_type: str = DEFAULT_TOOL_TRACE_ACTIVITY_TYPE,
) -> Iterator[str]:
    """Apply ``ev`` to ``state`` and yield one ``ACTIVITY_SNAPSHOT`` SSE line."""
    state.apply(ev)
    yield agui_stream.agui_activity_snapshot(
        message_id=message_id,
        activity_type=activity_type,
        content=state.to_content(),
        replace=True,
        timestamp=ev.ts_ms,
    )


class TraceEventChannel(str, Enum):
    """
    Where tool trace maps on the AG-UI wire:

    - ``PRE_ANSWER``: before assistant text — REASONING_*, STEP_*, CUSTOM (legacy / preface).
    - ``POST_ANSWER``: after assistant text started — STEP_* and CUSTOM only (no REASONING_*).
    """

    PRE_ANSWER = "pre_answer"
    POST_ANSWER = "post_answer"


def trace_events_to_sse_frames(
    events: list[TraceEvent] | TraceEvent,
    *,
    reasoning_message_id: str,
    channel: TraceEventChannel = TraceEventChannel.PRE_ANSWER,
) -> Iterator[str]:
    """Yield ``data:`` SSE lines for one or more trace events."""
    if isinstance(events, TraceEvent):
        seq = [events]
    else:
        seq = events
    for ev in seq:
        yield from _map_one(
            ev,
            reasoning_message_id=reasoning_message_id,
            channel=channel,
        )


def _map_one(
    ev: TraceEvent,
    *,
    reasoning_message_id: str,
    channel: TraceEventChannel,
) -> Iterator[str]:
    ts = ev.ts_ms
    if ev.kind == TraceKind.STEP_STARTED:
        name = str(ev.payload.get("step_name") or "step")
        yield agui_stream.agui_step_started(step_name=name, timestamp=ts)
    elif ev.kind == TraceKind.STEP_FINISHED:
        name = str(ev.payload.get("step_name") or "step")
        yield agui_stream.agui_step_finished(step_name=name, timestamp=ts)
    elif ev.kind == TraceKind.REASONING_LINE:
        if channel == TraceEventChannel.POST_ANSWER:
            return
        text = str(ev.payload.get("text") or "")
        if not text:
            return
        yield agui_stream.agui_reasoning_message_content(
            message_id=reasoning_message_id,
            delta=text if text.endswith("\n") else f"{text}\n",
            timestamp=ts,
        )
    elif ev.kind == TraceKind.MODEL_REASONING_DELTA:
        if channel == TraceEventChannel.POST_ANSWER:
            return
        text = str(ev.payload.get("text") or "")
        if not text:
            return
        yield agui_stream.agui_reasoning_message_content(
            message_id=reasoning_message_id,
            delta=text if text.endswith("\n") else f"{text}\n",
            timestamp=ts,
        )
    elif ev.kind == TraceKind.CUSTOM:
        yield agui_stream.agui_custom(
            name=str(ev.payload.get("name") or "trace"),
            value=ev.payload.get("value"),
            timestamp=ts,
        )
