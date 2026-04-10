"""Bedrock trace lines from Strands ``ModelStreamChunkEvent`` (raw ConverseStream chunks)."""

from __future__ import annotations

from smart_report_analyst.service.strands.runner import (
    _bedrock_trace_lines_from_model_stream_chunk_event,
)


def test_chunk_event_message_stop_only() -> None:
    lines = _bedrock_trace_lines_from_model_stream_chunk_event(
        {"event": {"messageStop": {"stopReason": "tool_use"}}}
    )
    assert lines == ["stop_reason=tool_use\n"]


def test_chunk_event_metadata_only() -> None:
    lines = _bedrock_trace_lines_from_model_stream_chunk_event(
        {
            "event": {
                "metadata": {
                    "usage": {
                        "inputTokens": 47,
                        "outputTokens": 20,
                        "totalTokens": 67,
                    },
                    "metrics": {"latencyMs": 100.0},
                }
            }
        }
    )
    assert lines == [
        "usage: input_tokens=47  output_tokens=20  total_tokens=67 "
        "metrics: latency_ms=100.0\n"
    ]


def test_chunk_event_both_message_stop_and_metadata_one_frame() -> None:
    lines = _bedrock_trace_lines_from_model_stream_chunk_event(
        {
            "event": {
                "messageStop": {"stopReason": "end_turn"},
                "metadata": {
                    "usage": {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3},
                    "metrics": {},
                },
            }
        }
    )
    assert lines == ["stop_reason=end_turn\n", "usage: input_tokens=1  output_tokens=2  total_tokens=3\n"]


def test_chunk_event_rejects_non_model_stream_shape() -> None:
    assert _bedrock_trace_lines_from_model_stream_chunk_event({"data": "x"}) == []
    assert _bedrock_trace_lines_from_model_stream_chunk_event({"event": "bad"}) == []
    assert _bedrock_trace_lines_from_model_stream_chunk_event({"event": {}, "extra": 1}) == []
