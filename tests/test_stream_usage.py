"""Bedrock usage helpers on ``runner`` (Strands ModelStopReason)."""

from __future__ import annotations

from smart_report_analyst.service.strands.runner import (
    _format_bedrock_usage_trace,
    _try_extract_model_stop_payload,
)


def test_try_extract_model_stop_payload_accepts_strands_shape() -> None:
    ev = {
        "stop": (
            "end_turn",
            {"role": "assistant", "content": []},
            {"inputTokens": 47, "outputTokens": 20, "totalTokens": 67},
            {"latencyMs": 100.0},
        )
    }
    out = _try_extract_model_stop_payload(ev)
    assert out is not None
    reason, usage, metrics = out
    assert reason == "end_turn"
    assert usage["totalTokens"] == 67
    assert metrics["latencyMs"] == 100.0


def test_try_extract_model_stop_payload_rejects_plain_dict() -> None:
    assert _try_extract_model_stop_payload({"data": "x"}) is None
    assert _try_extract_model_stop_payload({"stop": "bad"}) is None


def test_format_bedrock_usage_trace_one_line() -> None:
    text = _format_bedrock_usage_trace(
        "tool_use",
        {"inputTokens": 47, "outputTokens": 20, "totalTokens": 67},
        {"latencyMs": 100.0},
    )
    assert text == (
        "stop_reason=tool_use "
        "usage: input_tokens=47  output_tokens=20  total_tokens=67 "
        "metrics: latency_ms=100.0\n"
    )


def test_format_bedrock_usage_trace_omits_metrics_when_no_latency() -> None:
    text = _format_bedrock_usage_trace(
        "end_turn",
        {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3},
        {},
    )
    assert "metrics:" not in text
    assert "stop_reason=end_turn" in text
