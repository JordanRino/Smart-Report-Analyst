"""Tests for Strands session disk layout helpers used by /history and CopilotKit get_state."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from strands.types.content import Message
from strands.types.session import SessionMessage

from smart_report_analyst.service.strands.session import reader as reader_mod


def test_list_history_sessions_empty_dir(tmp_path: Path) -> None:
    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        assert reader_mod.list_history_sessions() == []


def test_list_history_sessions_finds_session_dirs(tmp_path: Path) -> None:
    sid = "abc12345-dead-beef-0000-000000000001"
    session_dir = tmp_path / f"session_{sid}"
    session_dir.mkdir()
    (session_dir / "session.json").write_text(json.dumps({"session_id": sid}), encoding="utf-8")

    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        rows = reader_mod.list_history_sessions()

    assert len(rows) == 1
    assert rows[0]["id"] == sid
    assert sid[:8] in rows[0]["name"]


def test_session_messages_to_copilot_messages_user_assistant() -> None:
    user_msg: Message = {
        "role": "user",
        "content": [{"text": "Hello"}],
    }
    asst_msg: Message = {
        "role": "assistant",
        "content": [{"text": "Hi there"}],
    }
    sms = [
        SessionMessage.from_message(user_msg, 0),
        SessionMessage.from_message(asst_msg, 1),
    ]
    out = reader_mod.session_messages_to_copilot_messages(sms)
    assert len(out) == 2
    assert out[0]["type"] == "TextMessage"
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "Hello"
    assert out[1]["role"] == "assistant"
    assert out[1]["content"] == "Hi there"


def test_get_copilot_state_for_thread_missing_session(tmp_path: Path) -> None:
    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        state = reader_mod.get_copilot_state_for_thread("nonexistent-id")

    assert state["threadExists"] is False
    assert state["messages"] == []
