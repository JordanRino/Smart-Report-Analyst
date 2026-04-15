"""Saved items catalog: SQLite + per-id files on disk.

Two kinds:
  - ``record`` — raw SQL result saved as CSV (from Records card in chat).
  - ``report`` — narrative PDF from the report_builder agent.

Both use the same ``saved_reports`` table and ``files/{id}/`` directory layout.
The ``kind`` column distinguishes them. The ``payload_sha256`` column prevents
duplicates — any save attempt with a matching hash returns the existing row.
"""

from __future__ import annotations

import csv
import hashlib
import io
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

KIND_RECORD = "record"
KIND_REPORT = "report"

_UUID_VERSION = 4


def _repo_root_from_this_file() -> Path:
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
  main_agent_id TEXT,
  kind TEXT NOT NULL DEFAULT 'report'
);

CREATE INDEX IF NOT EXISTS idx_saved_reports_created ON saved_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_saved_reports_thread ON saved_reports(thread_id);
CREATE INDEX IF NOT EXISTS idx_saved_reports_kind ON saved_reports(kind);
"""


def _connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_catalog_path(root)), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent column additions for DBs created before this schema version."""
    cur = conn.execute("PRAGMA table_info(saved_reports)")
    names = {row[1] for row in cur.fetchall()}
    if not names:
        return
    if "main_agent_id" not in names:
        conn.execute("ALTER TABLE saved_reports ADD COLUMN main_agent_id TEXT")
    if "kind" not in names:
        conn.execute(
            "ALTER TABLE saved_reports ADD COLUMN kind TEXT NOT NULL DEFAULT 'report'"
        )


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)
    _migrate(conn)
    conn.execute(
        "INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('version', '1')",
    )
    conn.commit()


def _payload_sha256(data: dict[str, Any]) -> str:
    """Stable SHA-256 of the canonical payload (deterministic JSON, sorted keys)."""
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _record_payload_sha256(results: list[Any], executed_sql: str) -> str:
    return _payload_sha256({"executed_sql": executed_sql, "results": results})


def _report_payload_sha256(markdown_content: str, title: str) -> str:
    return _payload_sha256({"markdown_content": markdown_content, "title": title})


def _parse_uuid(report_id: str) -> uuid.UUID:
    u = uuid.UUID(report_id)
    if u.version != _UUID_VERSION:
        raise ValueError("report id must be a UUID4")
    return u


def _results_to_csv(results: list[Any]) -> bytes:
    """Serialize a list of row dicts to UTF-8 CSV bytes."""
    if not results:
        return b""
    buf = io.StringIO()
    keys = list(results[0].keys()) if isinstance(results[0], dict) else []
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for row in results:
        writer.writerow(row if isinstance(row, dict) else {})
    return buf.getvalue().encode("utf-8")


class ReportsStore:
    """Saved items (records + reports) under one storage root."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else resolved_reports_storage_root()

    @property
    def root(self) -> Path:
        return self._root

    def _conn(self) -> sqlite3.Connection:
        c = _connect(self._root)
        _ensure_schema(c)
        return c

    def _find_by_sha256(
        self, conn: sqlite3.Connection, sha256: str, kind: str
    ) -> dict[str, Any] | None:
        row = conn.execute(
            "SELECT * FROM saved_reports WHERE payload_sha256 = ? AND kind = ?",
            (sha256, kind),
        ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Records (CSV)
    # ------------------------------------------------------------------

    def save_record(
        self,
        *,
        results: list[Any],
        executed_sql: str,
        refined_user_question: str | None,
        row_count: int | None,
        thread_id: str,
        agent_id: str,
        title: str | None = None,
        source_message_id: str | None = None,
        main_agent_id: str | None = None,
    ) -> dict[str, Any]:
        if not thread_id.strip():
            raise ReportPdfClientError("thread_id is required")
        if not agent_id.strip():
            raise ReportPdfClientError("agent_id is required")
        if len(results) > MAX_RESULT_ROWS:
            raise ReportPdfClientError(f"Too many rows (max {MAX_RESULT_ROWS})")

        pay_sha = _record_payload_sha256(results, executed_sql)
        conn = self._conn()
        try:
            existing = self._find_by_sha256(conn, pay_sha, KIND_RECORD)
            if existing:
                return {**existing, "already_exists": True}

            display_title = (title or "").strip() or (
                (refined_user_question or "").strip() or "Saved record"
            )
            main_raw = (main_agent_id or "").strip() or None
            rid = str(uuid.uuid4())
            now_ms = int(time.time() * 1000)
            csv_bytes = _results_to_csv(results)
            csv_sha = hashlib.sha256(csv_bytes).hexdigest()
            sql_row_count = row_count if isinstance(row_count, int) else len(results)

            files_dir = _files_dir(self._root, rid)
            files_dir.mkdir(parents=True, exist_ok=True)

            csv_path = files_dir / "records.csv"
            csv_path.write_bytes(csv_bytes)

            snapshot = {
                "executed_sql": executed_sql,
                "results": results,
                "refined_user_question": refined_user_question,
                "row_count": row_count,
            }
            (files_dir / "snapshot.json").write_text(
                json.dumps(snapshot, indent=2, default=str), encoding="utf-8"
            )

            conn.execute(
                """
                INSERT INTO saved_reports (
                  id, created_at, updated_at, thread_id, agent_id, title,
                  executed_sql, row_count, results_row_count,
                  payload_sha256, pdf_sha256, pdf_size_bytes,
                  source_message_id, main_agent_id, kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid, now_ms, now_ms,
                    thread_id.strip(), agent_id.strip(),
                    display_title[:500],
                    (executed_sql or "")[:500_000],
                    sql_row_count, len(results),
                    pay_sha, csv_sha, len(csv_bytes),
                    (source_message_id or "").strip() or None,
                    main_raw, KIND_RECORD,
                ),
            )
            conn.commit()
        except Exception:
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
            "kind": KIND_RECORD,
            "already_exists": False,
        }

    # ------------------------------------------------------------------
    # Reports (PDF from report_builder)
    # ------------------------------------------------------------------

    def save_report_from_markdown(
        self,
        *,
        pdf_bytes: bytes,
        markdown_content: str,
        title: str,
        thread_id: str,
        agent_id: str,
        source_message_id: str | None = None,
        main_agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Persist a pre-rendered PDF from the report_builder agent."""
        if not thread_id.strip():
            raise ReportPdfClientError("thread_id is required")
        if not agent_id.strip():
            raise ReportPdfClientError("agent_id is required")
        if not pdf_bytes:
            raise ReportPdfClientError("pdf_bytes must not be empty")

        pay_sha = _report_payload_sha256(markdown_content, title)
        conn = self._conn()
        try:
            existing = self._find_by_sha256(conn, pay_sha, KIND_REPORT)
            if existing:
                return {**existing, "already_exists": True}

            main_raw = (main_agent_id or "").strip() or None
            rid = str(uuid.uuid4())
            now_ms = int(time.time() * 1000)
            pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()
            display_title = title.strip()[:500] or "Report"

            files_dir = _files_dir(self._root, rid)
            files_dir.mkdir(parents=True, exist_ok=True)
            tmp_pdf = files_dir / "report.pdf.tmp"
            tmp_pdf.write_bytes(pdf_bytes)
            tmp_pdf.replace(files_dir / "report.pdf")
            (files_dir / "snapshot.json").write_text(
                json.dumps({"markdown_content": markdown_content, "title": title}, indent=2),
                encoding="utf-8",
            )

            conn.execute(
                """
                INSERT INTO saved_reports (
                  id, created_at, updated_at, thread_id, agent_id, title,
                  executed_sql, row_count, results_row_count,
                  payload_sha256, pdf_sha256, pdf_size_bytes,
                  source_message_id, main_agent_id, kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid, now_ms, now_ms,
                    thread_id.strip(), agent_id.strip(),
                    display_title,
                    "",  # no SQL for narrative reports
                    None, 0,
                    pay_sha, pdf_sha, len(pdf_bytes),
                    (source_message_id or "").strip() or None,
                    main_raw, KIND_REPORT,
                ),
            )
            conn.commit()
        except Exception:
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
            "kind": KIND_REPORT,
            "already_exists": False,
        }

    # ------------------------------------------------------------------
    # Legacy SQL-result PDF save (kept for backward compat)
    # ------------------------------------------------------------------

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
        """Legacy: saves a PDF rendered from raw SQL results. Kept for the existing route."""
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
        main_raw = (main_agent_id or "").strip() or None
        pay_sha = _payload_sha256({
            "executed_sql": tool_result.get("executed_sql") or "",
            "results": results,
            "refined_user_question": tool_result.get("refined_user_question"),
            "row_count": tool_result.get("row_count"),
        })

        conn = self._conn()
        try:
            existing = self._find_by_sha256(conn, pay_sha, KIND_REPORT)
            if existing:
                return {**existing, "already_exists": True}

            rid = str(uuid.uuid4())
            now_ms = int(time.time() * 1000)
            pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()
            sql_row_count = (
                body.row_count if isinstance(body.row_count, int) else len(results)
            )
            files_dir = _files_dir(self._root, rid)
            files_dir.mkdir(parents=True, exist_ok=True)

            snapshot = {
                "executed_sql": tool_result.get("executed_sql") or "",
                "results": results,
                "refined_user_question": tool_result.get("refined_user_question"),
                "row_count": tool_result.get("row_count"),
            }
            (files_dir / "snapshot.json").write_text(
                json.dumps(snapshot, indent=2, default=str), encoding="utf-8"
            )
            tmp_pdf = files_dir / "report.pdf.tmp"
            tmp_pdf.write_bytes(pdf_bytes)
            tmp_pdf.replace(files_dir / "report.pdf")

            conn.execute(
                """
                INSERT INTO saved_reports (
                  id, created_at, updated_at, thread_id, agent_id, title,
                  executed_sql, row_count, results_row_count,
                  payload_sha256, pdf_sha256, pdf_size_bytes,
                  source_message_id, main_agent_id, kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid, now_ms, now_ms,
                    thread_id.strip(), agent_id.strip(),
                    display_title[:500],
                    str(tool_result.get("executed_sql") or "")[:500_000],
                    sql_row_count, len(results),
                    pay_sha, pdf_sha, len(pdf_bytes),
                    (source_message_id or "").strip() or None,
                    main_raw, KIND_REPORT,
                ),
            )
            conn.commit()
        except Exception:
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
            "kind": KIND_REPORT,
            "already_exists": False,
        }

    # ------------------------------------------------------------------
    # List / read / delete
    # ------------------------------------------------------------------

    def list_reports(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        thread_id: str | None = None,
        agent_id: str | None = None,
        kind: str | None = None,
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
            if kind and kind.strip() in (KIND_RECORD, KIND_REPORT):
                where.append("kind = ?")
                params.append(kind.strip())
            wh = (" WHERE " + " AND ".join(where)) if where else ""

            cur = conn.execute(f"SELECT COUNT(*) AS c FROM saved_reports{wh}", params)
            total = int(cur.fetchone()["c"])

            params2 = list(params) + [limit, offset]
            rows = conn.execute(
                f"""
                SELECT id, created_at, updated_at, thread_id, agent_id, title,
                       executed_sql, row_count, results_row_count,
                       payload_sha256, pdf_sha256, pdf_size_bytes,
                       source_message_id, main_agent_id, kind
                FROM saved_reports
                {wh}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params2,
            ).fetchall()
            return [dict(r) for r in rows], total
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
                "main_agent_id, kind "
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

    def get_csv_path(self, report_id: str) -> Path | None:
        _parse_uuid(report_id)
        p = _files_dir(self._root, report_id) / "records.csv"
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
