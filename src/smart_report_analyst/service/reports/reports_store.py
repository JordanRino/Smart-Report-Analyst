"""Saved SQL reports: SQLite catalog + per-id PDF and snapshot files on disk."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.reports.report_pdf import (
    MAX_RESULT_ROWS,
    ReportPdfClientError,
    ReportPdfRequest,
    render_sql_report_pdf,
)

_UUID_VERSION = 4


def _repo_root_from_this_file() -> Path:
    # reports_store.py -> reports -> service -> smart_report_analyst -> src -> repo
    return Path(__file__).resolve().parents[4]


def resolved_reports_storage_root() -> Path:
    settings = get_settings()
    if settings.REPORTS_STORAGE_DIR:
        return Path(settings.REPORTS_STORAGE_DIR).expanduser().resolve()
    return (_repo_root_from_this_file() / "reports" / "storage").resolve()


def _catalog_path(root: Path) -> Path:
    return root / "catalog.sqlite"


def _files_dir(root: Path, report_id: str) -> Path:
    return root / "files" / report_id


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_reports (
  id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  thread_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  title TEXT NOT NULL,
  executed_sql TEXT NOT NULL,
  row_count INTEGER,
  results_row_count INTEGER NOT NULL,
  payload_sha256 TEXT NOT NULL,
  pdf_sha256 TEXT NOT NULL,
  pdf_size_bytes INTEGER NOT NULL,
  source_message_id TEXT,
  main_agent_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_saved_reports_created ON saved_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_saved_reports_thread ON saved_reports(thread_id);
"""


def _connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_catalog_path(root)), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate_saved_reports_main_agent(conn: sqlite3.Connection) -> None:
    """Add ``main_agent_id`` for DBs created before orchestrator attribution."""
    cur = conn.execute("PRAGMA table_info(saved_reports)")
    names = {row[1] for row in cur.fetchall()}
    if names and "main_agent_id" not in names:
        conn.execute("ALTER TABLE saved_reports ADD COLUMN main_agent_id TEXT")


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)
    _migrate_saved_reports_main_agent(conn)
    conn.execute(
        "INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('version', '1')",
    )
    conn.commit()


def _payload_sha256(tool_result: dict[str, Any]) -> str:
    payload = {
        "executed_sql": tool_result.get("executed_sql") or "",
        "results": tool_result.get("results") or [],
        "refined_user_question": tool_result.get("refined_user_question"),
        "row_count": tool_result.get("row_count"),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_uuid(report_id: str) -> uuid.UUID:
    u = uuid.UUID(report_id)
    if u.version != _UUID_VERSION:
        raise ValueError("report id must be a UUID4")
    return u


class ReportsStore:
    """Saved reports under one storage root (for tests pass ``root=``)."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else resolved_reports_storage_root()

    @property
    def root(self) -> Path:
        return self._root

    def _conn(self) -> sqlite3.Connection:
        c = _connect(self._root)
        _ensure_schema(c)
        return c

    def save_report(
        self,
        *,
        body: ReportPdfRequest,
        thread_id: str,
        agent_id: str,
        title: str | None,
        source_message_id: str | None,
        main_agent_id: str | None = None,
    ) -> dict[str, Any]:
        if not thread_id.strip():
            raise ReportPdfClientError("thread_id is required")
        if not agent_id.strip():
            raise ReportPdfClientError("agent_id is required")

        pdf_bytes, _disp = render_sql_report_pdf(body)
        tool_result = body.to_tool_result()
        results = tool_result.get("results") or []
        if len(results) > MAX_RESULT_ROWS:
            raise ReportPdfClientError(f"Too many rows (max {MAX_RESULT_ROWS})")

        display_title = (title or "").strip() or (
            str(tool_result.get("refined_user_question") or "").strip()
            or body.fallback_user_question()
        )
        if not display_title:
            display_title = "Saved report"

        main_raw = (main_agent_id or "").strip() or None

        rid = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()
        pay_sha = _payload_sha256(tool_result)
        sql_row_count = (
            body.row_count if isinstance(body.row_count, int) else len(results)
        )

        files_dir = _files_dir(self._root, rid)
        snapshot = {
            "executed_sql": tool_result.get("executed_sql") or "",
            "results": results,
            "refined_user_question": tool_result.get("refined_user_question"),
            "row_count": tool_result.get("row_count"),
        }

        conn = self._conn()
        try:
            files_dir.mkdir(parents=True, exist_ok=True)
            snap_path = files_dir / "snapshot.json"
            pdf_path = files_dir / "report.pdf"
            tmp_pdf = files_dir / "report.pdf.tmp"
            snap_path.write_text(
                json.dumps(snapshot, indent=2, default=str),
                encoding="utf-8",
            )
            tmp_pdf.write_bytes(pdf_bytes)
            tmp_pdf.replace(pdf_path)

            conn.execute(
                """
                INSERT INTO saved_reports (
                  id, created_at, updated_at, thread_id, agent_id, title,
                  executed_sql, row_count, results_row_count,
                  payload_sha256, pdf_sha256, pdf_size_bytes, source_message_id,
                  main_agent_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    now_ms,
                    now_ms,
                    thread_id.strip(),
                    agent_id.strip(),
                    display_title[:500],
                    str(tool_result.get("executed_sql") or "")[:500_000],
                    sql_row_count,
                    len(results),
                    pay_sha,
                    pdf_sha,
                    len(pdf_bytes),
                    (source_message_id or "").strip() or None,
                    main_raw,
                ),
            )
            conn.commit()
        except Exception:
            if files_dir.exists():
                shutil.rmtree(files_dir, ignore_errors=True)
            conn.rollback()
            raise
        finally:
            conn.close()

        return {
            "id": rid,
            "created_at": now_ms,
            "title": display_title,
            "thread_id": thread_id.strip(),
            "agent_id": agent_id.strip(),
            "main_agent_id": main_raw,
        }

    def list_reports(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        thread_id: str | None = None,
        agent_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        limit = max(1, min(100, limit))
        offset = max(0, offset)
        conn = self._conn()
        try:
            where: list[str] = []
            params: list[Any] = []
            if thread_id and thread_id.strip():
                where.append("thread_id = ?")
                params.append(thread_id.strip())
            if agent_id and agent_id.strip():
                where.append("agent_id = ?")
                params.append(agent_id.strip())
            wh = (" WHERE " + " AND ".join(where)) if where else ""

            cur = conn.execute(f"SELECT COUNT(*) AS c FROM saved_reports{wh}", params)
            total = int(cur.fetchone()["c"])

            params2 = list(params)
            params2.extend([limit, offset])
            rows = conn.execute(
                f"""
                SELECT id, created_at, updated_at, thread_id, agent_id, title,
                       executed_sql, row_count, results_row_count,
                       payload_sha256, pdf_sha256, pdf_size_bytes, source_message_id,
                       main_agent_id
                FROM saved_reports
                {wh}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params2,
            ).fetchall()
            out = [dict(r) for r in rows]
            return out, total
        finally:
            conn.close()

    def get_metadata(self, report_id: str) -> dict[str, Any] | None:
        _parse_uuid(report_id)
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT id, created_at, updated_at, thread_id, agent_id, title, "
                "executed_sql, row_count, results_row_count, "
                "payload_sha256, pdf_sha256, pdf_size_bytes, source_message_id, "
                "main_agent_id "
                "FROM saved_reports WHERE id = ?",
                (report_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_pdf_path(self, report_id: str) -> Path | None:
        _parse_uuid(report_id)
        p = _files_dir(self._root, report_id) / "report.pdf"
        return p if p.is_file() else None

    def delete_report(self, report_id: str) -> bool:
        _parse_uuid(report_id)
        conn = self._conn()
        try:
            cur = conn.execute("DELETE FROM saved_reports WHERE id = ?", (report_id,))
            conn.commit()
            deleted = cur.rowcount > 0
        finally:
            conn.close()
        if deleted:
            shutil.rmtree(_files_dir(self._root, report_id), ignore_errors=True)
        return deleted
