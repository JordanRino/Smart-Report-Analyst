"""Tests for KB retrieval trace preview formatting."""

from __future__ import annotations

from smart_report_analyst.service.bedrock.kb_manager import (
    format_kb_trace_preview,
    parse_kb_retrieval_chunks,
)


def test_parse_kb_retrieval_chunks_multiple() -> None:
    raw = (
        "--- Chunk 1 (score=1.0) ---\n"
        "first body\n"
        "--- Chunk 2 (score=0.5) ---\n"
        "second body\n"
        "--- Chunk 3 (score=0.5) ---\n"
        "third\n"
    )
    chunks = parse_kb_retrieval_chunks(raw)
    assert len(chunks) == 3
    assert chunks[0].index == 1 and chunks[0].score == "1.0"
    assert "first body" in chunks[0].body
    assert chunks[2].index == 3


def test_format_kb_trace_preview_truncates_rest_and_per_chunk() -> None:
    raw = (
        "--- Chunk 1 (score=1.0) ---\n"
        + ("A" * 100)
        + "\n--- Chunk 2 (score=1.0) ---\n"
        + ("B" * 50)
        + "\n--- Chunk 3 (score=0.5) ---\n"
        + "tail\n"
    )
    preview = format_kb_trace_preview(
        raw, max_chunks=2, max_chars_per_chunk=40
    )
    assert preview is not None
    assert "Chunk 1" in preview
    assert "Chunk 2" in preview
    assert "Chunk 3" not in preview
    assert "more chunk" in preview.lower()
    assert preview.count("...") >= 1


def test_parse_unmarked_falls_back_to_single_chunk() -> None:
    raw = "plain text without markers"
    assert len(parse_kb_retrieval_chunks(raw)) == 1
    preview = format_kb_trace_preview(raw, max_chunks=2)
    assert preview is not None
    assert "plain text" in preview
