"""AG-UI wire format + SSE framing for CopilotKit / @ag-ui/client HTTP streams.

``@ag-ui/client`` parses the response with ``parseSSEStream``: each event must appear as
``data: <json>`` and events are separated by a blank line (``\\n\\n``). Raw NDJSON lines
from ``copilotkit.protocol.emit_runtime_event`` are not consumed incrementally.

Events must match ``@ag-ui/core`` ``EventSchemas`` (e.g. ``TEXT_MESSAGE_CONTENT`` with
``delta``, not Copilot's ``TextMessageContent`` with ``content``). The stream must start
with ``RUN_STARTED`` and end with ``RUN_FINISHED`` or ``RUN_ERROR`` (``verifyEvents``).
"""

from __future__ import annotations

import json
from typing import Any


def agui_sse_event(payload: dict[str, Any]) -> str:
    """One SSE frame: ``data: {...}\\n\\n`` (no spaces after ``data:`` per client trim)."""
    line = json.dumps(payload, default=str, separators=(",", ":"))
    return f"data:{line}\n\n"


def agui_run_started(*, thread_id: str, run_id: str) -> str:
    return agui_sse_event(
        {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
    )


def agui_run_finished(*, thread_id: str, run_id: str, result: Any | None = None) -> str:
    body: dict[str, Any] = {
        "type": "RUN_FINISHED",
        "threadId": thread_id,
        "runId": run_id,
    }
    if result is not None:
        body["result"] = result
    return agui_sse_event(body)


def agui_text_message_start(*, message_id: str, role: str = "assistant") -> str:
    return agui_sse_event(
        {"type": "TEXT_MESSAGE_START", "messageId": message_id, "role": role}
    )


def agui_text_message_content(*, message_id: str, delta: str) -> str:
    if not delta:
        return ""
    return agui_sse_event(
        {"type": "TEXT_MESSAGE_CONTENT", "messageId": message_id, "delta": delta}
    )


def agui_text_message_end(*, message_id: str) -> str:
    return agui_sse_event({"type": "TEXT_MESSAGE_END", "messageId": message_id})


def agui_tool_call_start(
    *,
    tool_call_id: str,
    tool_call_name: str,
    parent_message_id: str | None = None,
) -> str:
    ev: dict[str, Any] = {
        "type": "TOOL_CALL_START",
        "toolCallId": tool_call_id,
        "toolCallName": tool_call_name,
    }
    if parent_message_id is not None:
        ev["parentMessageId"] = parent_message_id
    return agui_sse_event(ev)


def agui_tool_call_args(*, tool_call_id: str, delta: str) -> str:
    return agui_sse_event(
        {"type": "TOOL_CALL_ARGS", "toolCallId": tool_call_id, "delta": delta}
    )


def agui_tool_call_end(*, tool_call_id: str) -> str:
    return agui_sse_event({"type": "TOOL_CALL_END", "toolCallId": tool_call_id})


def agui_tool_call_result(
    *,
    message_id: str,
    tool_call_id: str,
    content: str,
) -> str:
    return agui_sse_event(
        {
            "type": "TOOL_CALL_RESULT",
            "messageId": message_id,
            "toolCallId": tool_call_id,
            "content": content,
            "role": "tool",
        }
    )


def agui_state_snapshot(*, snapshot: dict[str, Any]) -> str:
    return agui_sse_event({"type": "STATE_SNAPSHOT", "snapshot": snapshot})


__all__ = [
    "agui_run_finished",
    "agui_run_started",
    "agui_sse_event",
    "agui_state_snapshot",
    "agui_text_message_content",
    "agui_text_message_end",
    "agui_text_message_start",
    "agui_tool_call_args",
    "agui_tool_call_end",
    "agui_tool_call_result",
    "agui_tool_call_start",
]
