"""Run Strands conversation turns (streaming and sync)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncIterator

from smart_report_analyst.service.agent_trace.events import TraceEvent, TraceKind
from smart_report_analyst.service.strands.agents import create_strands_agent
from smart_report_analyst.service.strands.tools import StrandsTurnState
from smart_report_analyst.service.strands.session import build_strands_session_manager
from smart_report_analyst.service.strands.conversation import (
    build_strands_conversation_manager,
)
from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.strands.guardrails import classify_user_message


logger = logging.getLogger(__name__)

_STREAM_END = object()


def _summarize_stream_event_for_log(event: Any) -> str:
    """Compact shape description for diagnostics (no token dumps)."""
    if isinstance(event, dict):
        keys = list(event.keys())
        types_sample = {k: type(event[k]).__name__ for k in keys[:10]}
        return f"dict n_keys={len(keys)} keys_head={keys[:10]!r} value_types={types_sample!r}"
    return f"{type(event).__module__}.{type(event).__qualname__}"


def _validate_strands_settings() -> None:
    settings = get_settings()
    if not settings.BEDROCK_MODEL_ID:
        raise ValueError("BEDROCK_MODEL_ID is required when AGENT_BACKEND=strands")
    if not settings.BEDROCK_KNOWLEDGE_BASE_ID:
        raise ValueError("BEDROCK_KNOWLEDGE_BASE_ID is required when AGENT_BACKEND=strands")


async def _anext_or_sentinel(aiter: AsyncIterator[Any]) -> Any:
    try:
        return await aiter.__anext__()
    except StopAsyncIteration:
        return _STREAM_END


async def _merge_stream_with_trace_queue(
    stream_agen: AsyncIterator[Any],
    trace_queue: asyncio.Queue,
) -> AsyncIterator[tuple[str, Any]]:
    """
    Interleave Strands ``stream_async`` events with :class:`~smart_report_analyst.service.agent_trace.events.TraceEvent` items from ``trace_queue``.
    """
    pending_stream = asyncio.create_task(_anext_or_sentinel(stream_agen))
    pending_queue = asyncio.create_task(trace_queue.get())
    try:
        while True:
            done, _ = await asyncio.wait(
                {pending_stream, pending_queue},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if pending_queue in done:
                ev = pending_queue.result()
                yield ("trace", ev)
                pending_queue = asyncio.create_task(trace_queue.get())
            if pending_stream in done:
                item = pending_stream.result()
                if item is _STREAM_END:
                    break
                yield ("stream", item)
                pending_stream = asyncio.create_task(_anext_or_sentinel(stream_agen))
    finally:
        pending_queue.cancel()
        try:
            await pending_queue
        except asyncio.CancelledError:
            pass
        pending_stream.cancel()
        try:
            await pending_stream
        except asyncio.CancelledError:
            pass

    while True:
        try:
            ev = trace_queue.get_nowait()
            yield ("trace", ev)
        except asyncio.QueueEmpty:
            break


async def run_stream(
    user_message: str,
    session_id: str,
    *,
    run_id: str = "",
    agent_name: str = "loan_analyst_agent",
) -> AsyncIterator[dict[str, Any]]:
    """
    Async-iterate stream events compatible with CopilotKit

    Yields ``chunk``, ``trace`` (optional), and a final ``tool_result``.
    """
    _validate_strands_settings()
    logger.info(
        "strands_stream_turn",
        extra={
            "user_chars": len(user_message),
        },
    )
    if not user_message.strip():
        yield {"type": "chunk", "data": "No user message to process."}
        yield {"type": "tool_result", "data": {}}
        return

    topic = classify_user_message(user_message)
    if not topic.allowed:
        logger.info(
            "strands_topic_guardrail_block",
            extra={"reason": topic.reason, "detail": topic.detail},
        )
        yield {"type": "chunk", "data": topic.refusal_message}
        yield {"type": "tool_result", "data": {}}
        return

    turn_state = StrandsTurnState()
    trace_queue: asyncio.Queue = asyncio.Queue()
    turn_state.trace_queue = trace_queue
    turn_state.trace_run_id = run_id or ""
    turn_state.trace_thread_id = session_id
    turn_state.trace_agent_name = agent_name

    sm = build_strands_session_manager(session_id)
    cm = build_strands_conversation_manager()
    agent = create_strands_agent(
        turn_state,
        session_manager=sm,
        conversation_manager=cm,
    )

    last_result = None
    saw_text = False
    stream_event_count = 0
    non_dict_event_count = 0
    first_event_summary: str | None = None
    stream_trace_seq = 0

    stream_agen = agent.stream_async(user_message)
    async for kind, payload in _merge_stream_with_trace_queue(stream_agen, trace_queue):
        if kind == "trace":
            yield {"type": "trace", "data": payload}
            continue

        event = payload
        stream_event_count += 1
        if first_event_summary is None:
            first_event_summary = _summarize_stream_event_for_log(event)
        if not isinstance(event, dict):
            non_dict_event_count += 1
            continue
        rt = event.get("reasoningText")
        if isinstance(rt, str) and rt:
            stream_trace_seq += 1
            yield {
                "type": "trace",
                "data": TraceEvent(
                    run_id=run_id or "",
                    thread_id=session_id,
                    agent_name=agent_name,
                    step_id=stream_trace_seq,
                    ts_ms=int(time.time() * 1000),
                    kind=TraceKind.MODEL_REASONING_DELTA,
                    payload={"text": rt},
                ),
            }
        data = event.get("data")
        if isinstance(data, str) and data:
            saw_text = True
            yield {"type": "chunk", "data": data}
        if "result" in event:
            last_result = event.get("result")

    emitted_text_chunk = saw_text
    if not saw_text and last_result is not None:
        fallback = str(last_result).strip()
        if fallback:
            yield {"type": "chunk", "data": fallback}
            emitted_text_chunk = True

    if not emitted_text_chunk:
        logger.warning(
            "strands_stream_async_no_string_chunks: expected dict events with non-empty str "
            "'data' (see run_stream); events=%s non_dict=%s first=%s had_result_key=%s",
            stream_event_count,
            non_dict_event_count,
            first_event_summary,
            last_result is not None,
        )

    yield {"type": "tool_result", "data": turn_state.last_tool_result or {}}


def run_sync(
    user_message: str,
    session_id: str,
) -> dict[str, Any]:
    """Non-streaming turn for CLI."""

    _validate_strands_settings()
    logger.info(
        "strands_complete_turn",
        extra={
            "user_chars": len(user_message),
        },
    )
    if not user_message.strip():
        return {
            "final_response": "No user message to process.",
            "user_question": "",
            "tool_result": {},
        }

    topic = classify_user_message(user_message)
    if not topic.allowed:
        logger.info(
            "strands_topic_guardrail_block",
            extra={"reason": topic.reason, "detail": topic.detail},
        )
        return {
            "final_response": topic.refusal_message,
            "user_question": user_message,
            "tool_result": {},
        }

    turn_state = StrandsTurnState()

    sm = build_strands_session_manager(session_id)
    cm = build_strands_conversation_manager()
    agent = create_strands_agent(
        turn_state,
        session_manager=sm,
        conversation_manager=cm,
    )

    result = agent(user_message)
    final_text = str(result).strip()
    return {
        "final_response": final_text,
        "user_question": user_message,
        "tool_result": turn_state.last_tool_result or {},
    }
