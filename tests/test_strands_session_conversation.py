"""Strands session manager and conversation manager builders."""

from __future__ import annotations

from pathlib import Path

from strands.session.file_session_manager import FileSessionManager

from smart_report_analyst.config.settings import Settings
from smart_report_analyst.service.strands.conversation.manager import (
    build_strands_conversation_manager,
)
from smart_report_analyst.service.strands.session.manager import build_strands_session_manager


def test_build_strands_session_manager_uses_storage_dir_and_session_id(tmp_path: Path):
    settings = Settings.model_construct(
        STRANDS_SESSION_STORAGE_DIR=str(tmp_path),
        STRANDS_SESSION_PERSISTENCE=True,
    )
    sm = build_strands_session_manager(settings, "thread-abc")
    assert isinstance(sm, FileSessionManager)
    assert sm.session_id == "thread-abc"
    assert Path(sm.storage_dir) == tmp_path.resolve()


def test_build_strands_conversation_manager_uses_settings_ratios():
    settings = Settings.model_construct(
        STRANDS_CONVERSATION_SUMMARY_RATIO=0.4,
        STRANDS_CONVERSATION_PRESERVE_RECENT_MESSAGES=7,
    )
    cm = build_strands_conversation_manager(settings)
    assert cm.summary_ratio == 0.4
    assert cm.preserve_recent_messages == 7
