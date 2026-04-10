"""Agent trace mapper and merged stream ordering."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from smart_report_analyst.service.agent_trace.events import TraceEvent, TraceKind
from smart_report_analyst.service.strands.runner import _merge_stream_with_trace_queue


def test_trace_events_to_sse_step_and_reasoning() -> None:
    from smart_report_analyst.service.agent_trace.agui_mapper import trace_events_to_sse_frames

    rid = "reasoning-1"
    ev = TraceEvent(
        run_id="r1",
        thread_id="t1",
        agent_name="a",
        step_id=1,
        ts_ms=100,
        kind=TraceKind.STEP_STARTED,
        payload={"step_name": "tool:execute_sql"},
    )
    frames = list(trace_events_to_sse_frames(ev, reasoning_message_id=rid))
    assert len(frames) == 1
    body = json.loads(frames[0].replace("data:", "").strip())
    assert body["type"] == "STEP_STARTED"
    assert body["stepName"] == "tool:execute_sql"
    assert body["timestamp"] == 100


def test_trace_events_model_reasoning_delta_maps_like_reasoning_line() -> None:
    from smart_report_analyst.service.agent_trace.agui_mapper import trace_events_to_sse_frames

    rid = "reasoning-1"
    ev = TraceEvent(
        run_id="r1",
        thread_id="t1",
        agent_name="a",
        step_id=1,
        ts_ms=200,
        kind=TraceKind.MODEL_REASONING_DELTA,
        payload={"text": "model reasoning bit"},
    )
    frames = list(trace_events_to_sse_frames(ev, reasoning_message_id=rid))
    assert len(frames) == 1
    body = json.loads(frames[0].replace("data:", "").strip())
    assert body["type"] == "REASONING_MESSAGE_CONTENT"
    assert body["messageId"] == rid
    assert body["delta"] == "model reasoning bit\n"


def test_trace_events_reasoning_line_includes_elapsed_ms_prefix_when_payload_set() -> None:
    from smart_report_analyst.service.agent_trace.agui_mapper import trace_events_to_sse_frames

    rid = "reasoning-1"
    ev = TraceEvent(
        run_id="r1",
        thread_id="t1",
        agent_name="a",
        step_id=2,
        ts_ms=50,
        kind=TraceKind.REASONING_LINE,
        payload={"text": "usage: input_tokens=1\n", "trace_elapsed_ms": 1234},
    )
    frames = list(trace_events_to_sse_frames(ev, reasoning_message_id=rid))
    body = json.loads(frames[0].replace("data:", "").strip())
    assert body["delta"] == "[[trace:1234ms]] usage: input_tokens=1\n"


def test_trace_events_reasoning_line_plain_when_no_elapsed_payload() -> None:
    from smart_report_analyst.service.agent_trace.agui_mapper import trace_events_to_sse_frames

    rid = "reasoning-1"
    ev = TraceEvent(
        run_id="r1",
        thread_id="t1",
        agent_name="a",
        step_id=2,
        ts_ms=50,
        kind=TraceKind.REASONING_LINE,
        payload={"text": "no elapsed key\n"},
    )
    frames = list(trace_events_to_sse_frames(ev, reasoning_message_id=rid))
    body = json.loads(frames[0].replace("data:", "").strip())
    assert body["delta"] == "no elapsed key\n"


def test_trace_events_post_answer_skips_model_reasoning_delta() -> None:
    from smart_report_analyst.service.agent_trace.agui_mapper import (
        TraceEventChannel,
        trace_events_to_sse_frames,
    )

    rid = "reasoning-1"
    ev = TraceEvent(
        run_id="r1",
        thread_id="t1",
        agent_name="a",
        step_id=1,
        ts_ms=50,
        kind=TraceKind.MODEL_REASONING_DELTA,
        payload={"text": "no reasoning after close"},
    )
    frames = list(
        trace_events_to_sse_frames(
            ev,
            reasoning_message_id=rid,
            channel=TraceEventChannel.POST_ANSWER,
        )
    )
    assert frames == []


def test_trace_events_post_answer_skips_reasoning_line() -> None:
    from smart_report_analyst.service.agent_trace.agui_mapper import (
        TraceEventChannel,
        trace_events_to_sse_frames,
    )

    rid = "reasoning-1"
    ev = TraceEvent(
        run_id="r1",
        thread_id="t1",
        agent_name="a",
        step_id=1,
        ts_ms=50,
        kind=TraceKind.REASONING_LINE,
        payload={"text": "should not map to REASONING_MESSAGE_CONTENT"},
    )
    frames = list(
        trace_events_to_sse_frames(
            ev,
            reasoning_message_id=rid,
            channel=TraceEventChannel.POST_ANSWER,
        )
    )
    assert frames == []


def test_assert_no_reasoning_content_after_end_passes_and_fails() -> None:
    from smart_report_analyst.service.agent_trace.sse_reasoning_invariant import (
        assert_no_reasoning_content_after_end_for_same_message,
    )

    good = [
        'data:{"type":"REASONING_MESSAGE_CONTENT","messageId":"m1","delta":"a"}\n\n',
        'data:{"type":"REASONING_MESSAGE_END","messageId":"m1"}\n\n',
        'data:{"type":"REASONING_MESSAGE_CONTENT","messageId":"m2","delta":"b"}\n\n',
    ]
    assert_no_reasoning_content_after_end_for_same_message(good)

    bad = [
        'data:{"type":"REASONING_MESSAGE_END","messageId":"m1"}\n\n',
        'data:{"type":"REASONING_MESSAGE_CONTENT","messageId":"m1","delta":"late"}\n\n',
    ]
    with pytest.raises(AssertionError, match="REASONING_MESSAGE_CONTENT after"):
        assert_no_reasoning_content_after_end_for_same_message(bad)


def test_merge_stream_interleaves_trace_before_stream_end() -> None:
    async def stream() -> Any:
        yield {"data": "hi", "x": 1}
        yield {"result": None}

    async def _run() -> None:
        q: asyncio.Queue = asyncio.Queue()
        await q.put(
            TraceEvent(
                run_id="r",
                thread_id="t",
                agent_name="a",
                step_id=1,
                ts_ms=1,
                kind=TraceKind.REASONING_LINE,
                payload={"text": "trace line"},
            )
        )

        order: list[str] = []
        agen = stream().__aiter__()
        async for kind, _payload in _merge_stream_with_trace_queue(agen, q):
            if kind == "trace":
                order.append("trace")
            else:
                order.append("stream")

        assert order[0] == "trace"
        assert "stream" in order

    asyncio.run(_run())


def test_merge_stream_drains_queue_after_stream_finishes() -> None:
    async def gen() -> Any:
        yield {"data": "x"}

    async def _run() -> None:
        q: asyncio.Queue = asyncio.Queue()
        await q.put(
            TraceEvent(
                run_id="r",
                thread_id="t",
                agent_name="a",
                step_id=1,
                ts_ms=1,
                kind=TraceKind.STEP_STARTED,
                payload={"step_name": "late"},
            )
        )

        items: list[tuple[str, Any]] = []
        async for item in _merge_stream_with_trace_queue(gen(), q):
            items.append(item)

        kinds = [k for k, _ in items]
        assert "trace" in kinds
        assert "stream" in kinds

    asyncio.run(_run())
