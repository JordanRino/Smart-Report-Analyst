"""Tests for Strands session disk layout helpers used by /history and CopilotKit get_state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from strands.types.content import Message
from strands.types.session import SessionMessage

from smart_report_analyst.service.strands.session import reader as reader_mod
from smart_report_analyst.service.strands.session.scoped import composite_session_id


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


def test_logical_thread_id_strips_composite_suffix() -> None:
    tid = "550e8400-e29b-41d4-a716-446655440000"
    assert reader_mod.logical_thread_id(f"{tid}__sra_orchestrator_agent") == tid
    assert reader_mod.logical_thread_id(f"{tid}__sra_orchestrator_agent_ms_wlr_reporting_agent") == tid
    assert reader_mod.logical_thread_id(tid) == tid


def test_list_history_sessions_groups_composite_sessions_one_row(tmp_path: Path) -> None:
    """Orchestrator + sub-agent Strands dirs share one Copilot thread id."""
    tid = "a1b2c3d4-1111-2222-3333-444444444444"
    composites = [
        f"{tid}__sra_orchestrator_agent",
        f"{tid}__sra_orchestrator_agent_ms_wlr_reporting_agent",
        f"{tid}__sra_orchestrator_agent_report_builder",
    ]
    for i, cid in enumerate(composites):
        d = tmp_path / f"session_{cid}"
        d.mkdir()
        session_file = d / "session.json"
        session_file.write_text("{}", encoding="utf-8")
        # Deterministic mtimes: last composite is newest
        os.utime(session_file, (1000 + i, 1000 + i))

    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        rows = reader_mod.list_history_sessions()

    assert len(rows) == 1
    assert rows[0]["id"] == tid
    assert tid[:8] in rows[0]["name"]


def test_list_history_sessions_two_threads_sorted_by_newest(tmp_path: Path) -> None:
    t_old = "00000000-0000-0000-0000-000000000001"
    t_new = "11111111-1111-1111-1111-111111111111"
    for tid, mtime in ((t_old, 100.0), (t_new, 200.0)):
        d = tmp_path / f"session_{tid}__sra_orchestrator_agent"
        d.mkdir()
        p = d / "session.json"
        p.write_text("{}", encoding="utf-8")
        os.utime(p, (mtime, mtime))

    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        rows = reader_mod.list_history_sessions()

    assert len(rows) == 2
    assert rows[0]["id"] == t_new
    assert rows[1]["id"] == t_old


def test_session_messages_to_copilot_messages_drops_tool_noise() -> None:
    """Replay shows only text blocks; no [main_specialist] or [tool result]."""
    user_tool_only: Message = {
        "role": "user",
        "content": [
            {
                "toolResult": {
                    "toolUseId": "x",
                    "status": "success",
                    "content": [{"text": "sql output"}],
                }
            }
        ],
    }
    asst_text_and_tool: Message = {
        "role": "assistant",
        "content": [
            {"text": "I'll check that for you."},
            {
                "toolUse": {
                    "toolUseId": "t1",
                    "name": "main_specialist",
                    "input": {"input": "task"},
                }
            },
        ],
    }
    sms = [
        SessionMessage.from_message(user_tool_only, 0),
        SessionMessage.from_message(asst_text_and_tool, 1),
    ]
    out = reader_mod.session_messages_to_copilot_messages(sms)
    assert len(out) == 1
    assert out[0]["role"] == "assistant"
    assert out[0]["content"] == "I'll check that for you."
    assert "[main_specialist]" not in out[0]["content"]
    assert "tool result" not in (out[0]["content"] or "").lower()


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


def test_get_copilot_state_uses_on_disk_agent_id_not_copilot_name(tmp_path: Path) -> None:
    """Strands uses ``agent_default`` on disk; list_messages must use that id."""
    tid = "thread-uuid-0000-0000-0000-000000000001"
    orch = "sra_orchestrator_agent"
    strands_sid = composite_session_id(tid, orch)
    session_dir = tmp_path / f"session_{strands_sid}"
    session_dir.mkdir(parents=True)
    (session_dir / "session.json").write_text("{}", encoding="utf-8")
    (session_dir / "agents" / "agent_default").mkdir(parents=True)

    captured: list[tuple[str, str]] = []

    def fake_load(sid: str, agent_id: str):
        captured.append((sid, agent_id))
        return []

    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        with patch.object(reader_mod, "load_ordered_session_messages", side_effect=fake_load):
            reader_mod.get_copilot_state_for_thread(tid, agent_name=orch)

    assert captured == [(strands_sid, "default")]


def test_get_copilot_state_for_thread_missing_session(tmp_path: Path) -> None:
    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        state = reader_mod.get_copilot_state_for_thread("nonexistent-id")

    assert state["threadExists"] is False
    assert state["messages"] == []
