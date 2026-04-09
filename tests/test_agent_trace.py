"""Agent trace mapper and merged stream ordering."""

from __future__ import annotations

import asyncio
import json
from typing import Any

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
