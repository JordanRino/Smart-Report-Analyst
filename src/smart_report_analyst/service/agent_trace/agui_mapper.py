"""Map :class:`TraceEvent` to AG-UI SSE frame strings."""

from __future__ import annotations

from collections.abc import Iterator

from smart_report_analyst.integrations import agui_stream
from smart_report_analyst.service.agent_trace.events import TraceEvent, TraceKind


def trace_events_to_sse_frames(
    events: list[TraceEvent] | TraceEvent,
    *,
    reasoning_message_id: str,
) -> Iterator[str]:
    """Yield ``data:`` SSE lines for one or more trace events."""
    if isinstance(events, TraceEvent):
        seq = [events]
    else:
        seq = events
    for ev in seq:
        yield from _map_one(ev, reasoning_message_id=reasoning_message_id)


def _map_one(ev: TraceEvent, *, reasoning_message_id: str) -> Iterator[str]:
    ts = ev.ts_ms
    if ev.kind == TraceKind.STEP_STARTED:
        name = str(ev.payload.get("step_name") or "step")
        yield agui_stream.agui_step_started(step_name=name, timestamp=ts)
    elif ev.kind == TraceKind.STEP_FINISHED:
        name = str(ev.payload.get("step_name") or "step")
        yield agui_stream.agui_step_finished(step_name=name, timestamp=ts)
    elif ev.kind == TraceKind.REASONING_LINE:
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
