"""AG-UI connect replay (no full package import — avoids Python version mismatch in CI)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def _load_agui_stream_with_stub_reader():
    """Load ``agui_stream`` from source with a stub ``reader`` module."""
    root = Path(__file__).resolve().parents[1] / "src"
    reader_mod = types.ModuleType("smart_report_analyst.service.strands.session.reader")

    def get_copilot_state_for_thread(_thread_id: str) -> dict:
        return {
            "messages": [
                {
                    "type": "TextMessage",
                    "id": "m-user",
                    "role": "user",
                    "content": "Hello",
                },
                {
                    "type": "TextMessage",
                    "id": "m-asst",
                    "role": "assistant",
                    "content": "Hi",
                },
            ],
            "state": {"tool_result": {}},
        }

    reader_mod.get_copilot_state_for_thread = get_copilot_state_for_thread

    # Minimal package path so ``from smart_report_analyst...`` resolves.
    for name in (
        "smart_report_analyst",
        "smart_report_analyst.service",
        "smart_report_analyst.service.strands",
        "smart_report_analyst.service.strands.session",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["smart_report_analyst.service.strands.session.reader"] = reader_mod

    path = root / "smart_report_analyst" / "integrations" / "agui_stream.py"
    spec = importlib.util.spec_from_file_location(
        "agui_stream_under_test",
        path,
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agui_stream_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_iter_connect_replay_frames_replays_text_messages() -> None:
    agui = _load_agui_stream_with_stub_reader()
    frames = list(
        agui.iter_connect_replay_frames(thread_id="thread-1", run_id="run-1")
    )
    joined = "".join(frames)
    assert "RUN_STARTED" in joined
    assert "TEXT_MESSAGE_START" in joined
    assert "Hello" in joined
    assert "Hi" in joined
    assert "STATE_SNAPSHOT" in joined
    assert "RUN_FINISHED" in joined
