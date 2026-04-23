"""Strands tools: KB retrieve, SQL execution, and narrative report generation."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from strands import tool

from smart_report_analyst.config.settings import get_settings
from smart_report_analyst.service.agent_trace.events import TraceEvent, TraceKind
from smart_report_analyst.service.bedrock.kb_manager import KnowledgeBaseRetriever
from smart_report_analyst.service.persistence.mysql.app_data_layer import app_data_layer
from smart_report_analyst.service.bedrock.kb_manager import format_kb_trace_preview
from smart_report_analyst.service.reports.narrative_pdf import render_narrative_pdf
from smart_report_analyst.service.reports.reports_store import ReportsStore

logger = logging.getLogger(__name__)

_MAX_SQL_TRACE_CHARS = 2000


def _now_ms() -> int:
    return int(time.time() * 1000)


def _truncate_sql(q: str, limit: int = _MAX_SQL_TRACE_CHARS) -> str:
    t = q.strip()
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."


@dataclass
class StrandsTurnState:
    """Per-turn mutable state shared across orchestrator and sub-agents."""

    last_tool_result: dict = field(default_factory=dict)
    last_metadata_tool_result: dict = field(default_factory=dict)
    # Set by generate_report_pdf (report_id, title, …); agent.py emits deliver_report AG-UI when report_id is set.
    last_report_result: dict = field(default_factory=dict)
    # Copilot thread_id injected by runner so tools can use it without model passing it.
    thread_id: str = ""
    trace_queue: asyncio.Queue | None = None
    trace_run_id: str = ""
    trace_thread_id: str = ""
    trace_agent_name: str = ""
    trace_started_ms: int = 0
    _trace_step_seq: int = field(default=0, repr=False)
    _tool_step_seq: int = field(default=0, repr=False)

    def _next_step_id(self) -> int:
        self._trace_step_seq += 1
        return self._trace_step_seq

    def next_tool_step_name(self, tool: str) -> str:
        """Unique AG-UI step name per invocation (client forbids duplicate active stepName)."""
        self._tool_step_seq += 1
        return f"tool:{tool}:{self._tool_step_seq}"

    def mark_trace_elapsed_ms(self) -> int:
        """Ms since first ``REASONING_LINE`` of this turn (first line returns 0)."""
        now = _now_ms()
        if self.trace_started_ms == 0:
            self.trace_started_ms = now
            return 0
        return max(0, now - self.trace_started_ms)

    def _make_trace_event(self, kind: TraceKind, payload: dict[str, Any]) -> TraceEvent | None:
        if not self.trace_run_id or self.trace_queue is None:
            return None
        return TraceEvent(
            run_id=self.trace_run_id,
            thread_id=self.trace_thread_id,
            agent_name=self.trace_agent_name,
            step_id=self._next_step_id(),
            ts_ms=_now_ms(),
            kind=kind,
            payload=payload,
        )

    async def emit_trace_async(self, kind: TraceKind, payload: dict[str, Any]) -> None:
        if kind == TraceKind.REASONING_LINE:
            payload = {**payload, "trace_elapsed_ms": self.mark_trace_elapsed_ms()}
        ev = self._make_trace_event(kind, payload)
        if ev is None or self.trace_queue is None:
            return
        await self.trace_queue.put(ev)


def build_strands_tools(turn_state: StrandsTurnState) -> list:
    """Build tool callables bound to settings and turn-scoped result capture."""

    settings = get_settings()
    kb = KnowledgeBaseRetriever(settings)

    @tool
    async def retrieve_kb_context(query: str) -> str:
        """
        Search the Smart Report Analyst knowledge base for database metadata (tables, columns)
        and historical SQL examples. Call this before writing SQL when schema or similar queries matter.

        Async so trace events use ``await trace_queue.put`` on the same loop as ``run_stream``;
        blocking boto3 ``retrieve`` runs in ``asyncio.to_thread``.

        Args:
            query: Natural language search string (e.g. user question or table/column hints).

        Returns:
            Concatenated retrieval passages for the model to use.
        """
        t0 = _now_ms()
        step_name = turn_state.next_tool_step_name("retrieve_kb_context")
        await turn_state.emit_trace_async(
            TraceKind.STEP_STARTED, {"step_name": step_name}
        )
        await turn_state.emit_trace_async(
            TraceKind.REASONING_LINE,
            {"text": "Searching the knowledge base for schema and examples…"},
        )
        try:
            raw = await asyncio.to_thread(kb.retrieve, query)
            preview = format_kb_trace_preview(raw)
            if preview:
                await turn_state.emit_trace_async(
                    TraceKind.REASONING_LINE,
                    {"text": f"Knowledge base preview:\n{preview}\n"},
                )
            return raw
        finally:
            await turn_state.emit_trace_async(
                TraceKind.STEP_FINISHED, {"step_name": step_name}
            )
            dt = _now_ms() - t0
            if dt >= 0:
                await turn_state.emit_trace_async(
                    TraceKind.CUSTOM,
                    {
                        "name": "tool_timing_ms",
                        "value": {"tool": "retrieve_kb_context", "duration_ms": dt},
                    },
                )

    @tool
    async def execute_sql(query: str, user_refined_question: str, to_store: bool) -> dict:
        """
        Execute a SQL query against the SBA loan database directly via MySQL.

        Args:
            query: The SQL statement to run.
            user_refined_question: Clear, concise version of the user's analytical question.
            to_store: True if this question/SQL pair should be stored for future retrieval; false if duplicate.

        Returns:
            JSON object with executed_sql, results, row_count, refined_user_question, to_store.
        """
        t0 = _now_ms()
        step_name = turn_state.next_tool_step_name("execute_sql")
        await turn_state.emit_trace_async(
            TraceKind.STEP_STARTED, {"step_name": step_name}
        )
        await turn_state.emit_trace_async(
            TraceKind.REASONING_LINE,
            {"text": f"Running SQL ({_truncate_sql(query)})\n"},
        )
        try:
            body = await app_data_layer.execute_generated_query(
                query, user_refined_question, to_store
            )
            turn_state.last_tool_result = body
            rc = body.get("row_count", 0)
            await turn_state.emit_trace_async(
                TraceKind.REASONING_LINE,
                {"text": f"SQL finished: {rc} row(s) returned.\n"},
            )
            return body
        except Exception as e:
            logger.exception("execute_sql failed")
            err = {
                "error": True,
                "message": str(e),
                "refined_user_question": user_refined_question,
                "executed_sql": query,
                "results": [],
                "row_count": 0,
                "to_store": False,
            }
            turn_state.last_tool_result = err
            await turn_state.emit_trace_async(
                TraceKind.REASONING_LINE,
                {"text": f"SQL error: {str(e)[:200]}\n"},
            )
            return err
        finally:
            await turn_state.emit_trace_async(
                TraceKind.STEP_FINISHED, {"step_name": step_name}
            )
            dt = _now_ms() - t0
            if dt >= 0:
                await turn_state.emit_trace_async(
                    TraceKind.CUSTOM,
                    {
                        "name": "tool_timing_ms",
                        "value": {"tool": "execute_sql", "duration_ms": dt},
                    },
                )

    return [retrieve_kb_context, execute_sql]


def build_metadata_tools(turn_state: StrandsTurnState) -> list:
    """Tools for the orchestrator-attached metadata updater (session MySQL only)."""

    @tool
    async def execute_metadata_sql(query: str, user_refined_question: str, to_store: bool) -> dict:
        """
        Execute SQL for **session metadata** tables (upload-derived glossary / sidecar schema).

        Same JSON shape as ``execute_sql`` for the UI. Use **only** for DDL/DML against
        metadata tables (e.g. ``session_metadata`` scoped by ``thread_id``).

        Args:
            query: SQL to run (CREATE / INSERT / UPDATE / DELETE / SELECT as needed).
            user_refined_question: Short description of what this metadata change does.
            to_store: Same flag as ``execute_sql`` (typically false for metadata DDL).
        """
        t0 = _now_ms()
        step_name = turn_state.next_tool_step_name("execute_metadata_sql")
        await turn_state.emit_trace_async(
            TraceKind.STEP_STARTED, {"step_name": step_name}
        )
        await turn_state.emit_trace_async(
            TraceKind.REASONING_LINE,
            {"text": f"Running metadata SQL ({_truncate_sql(query)})\n"},
        )
        try:
            body = await app_data_layer.execute_metadata_sql(
                query, user_refined_question, to_store
            )
            turn_state.last_metadata_tool_result = body
            rc = body.get("row_count", 0)
            await turn_state.emit_trace_async(
                TraceKind.REASONING_LINE,
                {"text": f"Metadata SQL finished: {rc} row(s) returned.\n"},
            )
            return body
        except Exception as e:
            logger.exception("execute_metadata_sql failed")
            err = {
                "error": True,
                "message": str(e),
                "refined_user_question": user_refined_question,
                "executed_sql": query,
                "results": [],
                "row_count": 0,
                "to_store": False,
            }
            turn_state.last_metadata_tool_result = err
            await turn_state.emit_trace_async(
                TraceKind.REASONING_LINE,
                {"text": f"Metadata SQL error: {str(e)[:200]}\n"},
            )
            return err
        finally:
            await turn_state.emit_trace_async(
                TraceKind.STEP_FINISHED, {"step_name": step_name}
            )
            dt = _now_ms() - t0
            if dt >= 0:
                await turn_state.emit_trace_async(
                    TraceKind.CUSTOM,
                    {
                        "name": "tool_timing_ms",
                        "value": {"tool": "execute_metadata_sql", "duration_ms": dt},
                    },
                )

    return [execute_metadata_sql]


def build_report_builder_tools(turn_state: StrandsTurnState) -> list:
    """Tools available to the orchestrator for delivering narrative reports to the UI."""

    @tool
    async def generate_report_pdf(report_content: str, title: str) -> str:
        """
        Render a narrative markdown report to PDF, save it permanently, and deliver it
        as a report card in the chat UI.

        Call this AFTER the report_builder has produced its final markdown output and the
        user has confirmed the brief. Pass the complete markdown text and a concise title.

        Args:
            report_content: Full markdown text of the report (Title, Intro, Body, Summary sections).
            title: Short human-readable title for the report (used as filename and dashboard label).

        Returns:
            Confirmation string with the permanent report_id for the orchestrator to relay.
        """
        step_name = turn_state.next_tool_step_name("generate_report_pdf")
        await turn_state.emit_trace_async(TraceKind.STEP_STARTED, {"step_name": step_name})
        await turn_state.emit_trace_async(
            TraceKind.REASONING_LINE, {"text": f"Rendering PDF: {title!r}…\n"}
        )
        try:
            pdf_bytes = await asyncio.to_thread(render_narrative_pdf, report_content, title)

            # Auto-save permanently so the report survives navigation and history replay.
            store = ReportsStore()
            saved = await asyncio.to_thread(
                store.save_report_from_markdown,
                pdf_bytes=pdf_bytes,
                markdown_content=report_content,
                title=title,
                thread_id=turn_state.thread_id,
                agent_id="sra_orchestrator_agent",
            )
            report_id = saved["id"]

            turn_state.last_report_result = {
                "report_id": report_id,
                "title": title,
                "markdown_content": report_content,
            }
            await turn_state.emit_trace_async(
                TraceKind.REASONING_LINE,
                {"text": f"Report saved (id={report_id}).\n"},
            )
            return (
                f"Report saved successfully. report_id={report_id} title={title!r}. "
                "The report card will appear in the chat for the user to preview and download."
            )
        except Exception as exc:
            logger.exception("generate_report_pdf failed")
            return f"Report generation failed: {exc}"
        finally:
            await turn_state.emit_trace_async(
                TraceKind.STEP_FINISHED, {"step_name": step_name}
            )

    return [generate_report_pdf]
