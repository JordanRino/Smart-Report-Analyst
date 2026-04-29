"""In-process temp store for narrative report PDFs pending user save.

After the report_builder agent produces a PDF it is held here keyed by a
UUID ``temp_id``. The frontend fetches the PDF for preview/download and,
if the user clicks Save, the permanent save is triggered separately.

TTL: entries expire after ``_TTL_SECONDS`` (default 30 min). Cleanup runs
lazily on each access — no background thread required.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

_TTL_SECONDS: int = 30 * 60  # 30 minutes


@dataclass
class _TempEntry:
    pdf_bytes: bytes
    markdown_content: str
    title: str
    thread_id: str
    agent_id: str
    main_agent_id: str | None
    created_at: float = field(default_factory=time.monotonic)

    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > _TTL_SECONDS

    def to_meta(self, temp_id: str) -> dict[str, Any]:
        return {
            "temp_id": temp_id,
            "title": self.title,
            "thread_id": self.thread_id,
            "agent_id": self.agent_id,
            "main_agent_id": self.main_agent_id,
            "markdown_content": self.markdown_content,
        }


class _TempReportStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: dict[str, _TempEntry] = {}

    def _evict_expired(self) -> None:
        expired = [k for k, v in self._entries.items() if v.is_expired()]
        for k in expired:
            del self._entries[k]

    def put(
        self,
        *,
        pdf_bytes: bytes,
        markdown_content: str,
        title: str,
        thread_id: str,
        agent_id: str,
        main_agent_id: str | None = None,
    ) -> str:
        """Store a temp PDF and return a ``temp_id``."""
        temp_id = str(uuid.uuid4())
        entry = _TempEntry(
            pdf_bytes=pdf_bytes,
            markdown_content=markdown_content,
            title=title,
            thread_id=thread_id,
            agent_id=agent_id,
            main_agent_id=main_agent_id,
        )
        with self._lock:
            self._evict_expired()
            self._entries[temp_id] = entry
        return temp_id

    def get_pdf(self, temp_id: str) -> bytes | None:
        with self._lock:
            self._evict_expired()
            entry = self._entries.get(temp_id)
            if entry is None or entry.is_expired():
                return None
            return entry.pdf_bytes

    def get_meta(self, temp_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._evict_expired()
            entry = self._entries.get(temp_id)
            if entry is None or entry.is_expired():
                return None
            return entry.to_meta(temp_id)

    def pop(self, temp_id: str) -> _TempEntry | None:
        """Retrieve and remove an entry (used when permanently saving)."""
        with self._lock:
            self._evict_expired()
            return self._entries.pop(temp_id, None)


# Module-level singleton — one process, one store.
temp_report_store = _TempReportStore()
