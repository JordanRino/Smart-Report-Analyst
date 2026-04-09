"""Exercise ``run_stream`` and ``StrandsCopilotAgent.execute`` without Bedrock or AWS.

Patches the Strands agent factory and settings validation so CI / local dev can
verify trace + chunk merging and AG-UI framing.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

from smart_report_analyst.service.agent_trace.events import TraceEvent, TraceKind
from smart_report_analyst.service.strands.agent import StrandsCopilotAgent
from smart_report_analyst.service.strands.guardrails.classifier import TopicClassification
from smart_report_analyst.service.strands.runner import run_stream


def _sse_json_lines(frames: list[str]) -> list[dict]:
    out: list[dict] = []
    for fr in frames:
        for line in fr.splitlines():
            if line.startswith("data:"):
                out.append(json.loads(line[5:]))
    return out


@patch("smart_report_analyst.service.strands.runner.classify_user_message")
@patch("smart_report_analyst.service.strands.runner.create_strands_agent")
@patch("smart_report_analyst.service.strands.runner.build_strands_conversation_manager")
@patch("smart_report_analyst.service.strands.runner.build_strands_session_manager")
@patch("smart_report_analyst.service.strands.runner._validate_strands_settings")
def test_run_stream_merged_trace_and_chunks_without_bedrock(
    _mock_validate: MagicMock,
    _mock_sm: MagicMock,
    _mock_cm: MagicMock,
    mock_create: MagicMock,
    mock_classify: MagicMock,
) -> None:
    mock_classify.return_value = TopicClassification(
        allowed=True, reason="ok", refusal_message=""
    )

    def _factory(turn_state, session_manager=None, conversation_manager=None):
        _ = session_manager, conversation_manager

        class _FakeAgent:
            async def stream_async(self, _user_message: str):
                await turn_state.trace_queue.put(
                    TraceEvent(
                        run_id=turn_state.trace_run_id,
                        thread_id=turn_state.trace_thread_id,
                        agent_name=turn_state.trace_agent_name,
                        step_id=1,
                        ts_ms=42,
                        kind=TraceKind.REASONING_LINE,
                        payload={"text": "Synthetic trace line from mock agent\n"},
                    )
                )
                yield {"data": "mock-token"}

        return _FakeAgent()

    mock_create.side_effect = _factory

    async def _collect() -> list[dict]:
        rows: list[dict] = []
        async for ev in run_stream(
            "Show me loan counts",
            "thread-mock",
            run_id="run-mock",
            agent_name="test_agent",
        ):
            rows.append(ev)
        return rows

    rows = asyncio.run(_collect())

    types = [r["type"] for r in rows]
    assert "trace" in types
    assert "chunk" in types
    assert types[-1] == "tool_result"

    trace_events = [r["data"] for r in rows if r["type"] == "trace"]
    assert len(trace_events) == 1
    assert isinstance(trace_events[0], TraceEvent)
    assert trace_events[0].kind == TraceKind.REASONING_LINE

    chunks = [r["data"] for r in rows if r["type"] == "chunk"]
    assert chunks == ["mock-token"]

    mock_create.assert_called_once()


@patch("smart_report_analyst.service.strands.agent.run_stream")
def test_strands_copilot_agent_execute_uses_mock_run_stream(mock_run_stream: MagicMock) -> None:
    async def _fake_run_stream(
        user_message: str,
        session_id: str,
        *,
        run_id: str = "",
        agent_name: str = "",
    ):
        _ = user_message, session_id
        yield {
            "type": "trace",
            "data": TraceEvent(
                run_id=run_id or "r",
                thread_id=session_id,
                agent_name=agent_name,
                step_id=1,
                ts_ms=7,
                kind=TraceKind.STEP_STARTED,
                payload={"step_name": "tool:mock"},
            ),
        }
        yield {"type": "chunk", "data": "Synthetic answer."}
        yield {"type": "tool_result", "data": {}}

    mock_run_stream.side_effect = _fake_run_stream

    async def _run() -> list[str]:
        agent = StrandsCopilotAgent(name="test_agent")
        parts: list[str] = []
        async for frame in agent.execute(
            state={},
            messages=[{"role": "user", "content": "hello"}],
            thread_id="t1",
        ):
            parts.append(frame)
        return parts

    frames = asyncio.run(_run())
    events = _sse_json_lines(frames)
    types = [e["type"] for e in events]

    assert "RUN_STARTED" in types
    assert "REASONING_START" in types
    step_starts = [e for e in events if e["type"] == "STEP_STARTED"]
    step_names = {e.get("stepName") for e in step_starts}
    assert "strands_turn" in step_names
    assert "tool:mock" in step_names
    assert "TEXT_MESSAGE_CONTENT" in types
    assert "RUN_FINISHED" in types

    mock_run_stream.assert_called_once()
    call_kw = mock_run_stream.call_args
    assert call_kw[0][0] == "hello"
    assert call_kw[0][1] == "t1"
    assert call_kw[1]["agent_name"] == "test_agent"
