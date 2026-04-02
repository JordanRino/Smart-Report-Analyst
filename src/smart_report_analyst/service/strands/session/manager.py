"""Build Strands FileSessionManager for on-disk session persistence."""

from __future__ import annotations

from pathlib import Path

from strands.session.file_session_manager import FileSessionManager

from smart_report_analyst.config.settings import Settings


def _resolved_storage_dir(settings: Settings) -> Path:
    if settings.STRANDS_SESSION_STORAGE_DIR:
        return Path(settings.STRANDS_SESSION_STORAGE_DIR).expanduser().resolve()
    # Default: .../service/strands/storage
    return (Path(__file__).resolve().parent.parent / "storage").resolve()


def build_strands_session_manager(settings: Settings, session_id: str) -> FileSessionManager:
    """
    Session id should be the canonical chat id (e.g. Chainlit thread_id as str).

    Storage layout follows Strands FileSessionManager under ``storage_dir``.
    """
    storage_dir = _resolved_storage_dir(settings)
    storage_dir.mkdir(parents=True, exist_ok=True)
    return FileSessionManager(session_id=session_id, storage_dir=str(storage_dir))
