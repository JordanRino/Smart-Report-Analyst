"""delete_thread_strands_sessions and delete_orchestrator_state_file."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from smart_report_analyst.service.strands.session import orchestrator_state as orch_mod
from smart_report_analyst.service.strands.session import reader as reader_mod


def test_delete_thread_strands_sessions_removes_all_composite_dirs(tmp_path: Path) -> None:
    tid = "abc-1111-2222-3333-444444444444"
    orch = "sra_orchestrator_agent"
    for cid in (f"{tid}__{orch}", f"{tid}__{orch}_ms_wlr_reporting_agent"):
        d = tmp_path / f"session_{cid}"
        d.mkdir(parents=True)
        (d / "session.json").write_text("{}", encoding="utf-8")
    other = tmp_path / "session_other-thread__sra_orchestrator_agent"
    other.mkdir()
    (other / "session.json").write_text("{}", encoding="utf-8")

    with patch.object(reader_mod, "_resolved_storage_dir", return_value=tmp_path):
        n = reader_mod.delete_thread_strands_sessions(tid)

    assert n == 2
    assert not (tmp_path / f"session_{tid}__{orch}").exists()
    assert other.is_dir()


def test_delete_orchestrator_state_file_removes_orch_json(tmp_path: Path) -> None:
    tid = "def-0000-1111-2222-333333333333"
    p = tmp_path / f"orch_{tid}.json"
    p.write_text(json.dumps({"mainAgentId": "wlr_reporting_agent"}), encoding="utf-8")
    with patch.object(orch_mod, "_resolved_storage_dir", return_value=tmp_path):
        orch_mod.delete_orchestrator_state_file(tid)
    assert not p.is_file()
