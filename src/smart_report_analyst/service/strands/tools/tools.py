"""Strands tools: KB retrieve and SQL Lambda execution."""

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
    """Per-turn mutable state (last execute_sql result for UI + optional trace queue)."""

    last_tool_result: dict = field(default_factory=dict)
    trace_queue: asyncio.Queue | None = None
    main_loop: asyncio.AbstractEventLoop | None = None
    trace_run_id: str = ""
    trace_thread_id: str = ""
    trace_agent_name: str = ""
    _trace_step_seq: int = field(default=0, repr=False)

    def _next_step_id(self) -> int:
        self._trace_step_seq += 1
        return self._trace_step_seq

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

    def emit_trace_sync(self, kind: TraceKind, payload: dict[str, Any]) -> None:
        ev = self._make_trace_event(kind, payload)
        if ev is None:
            return
        self._schedule_put(ev)

    async def emit_trace_async(self, kind: TraceKind, payload: dict[str, Any]) -> None:
        ev = self._make_trace_event(kind, payload)
        if ev is None or self.trace_queue is None:
            return
        await self.trace_queue.put(ev)

    def _schedule_put(self, ev: TraceEvent) -> None:
        q = self.trace_queue
        loop = self.main_loop
        if q is None or loop is None:
            return

        async def _put() -> None:
            await q.put(ev)

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is loop:
            asyncio.create_task(_put())
            return

        def _done(fut: asyncio.Future[Any]) -> None:
            try:
                fut.result()
            except Exception:
                logger.debug("trace queue put failed", exc_info=True)

        try:
            fut = asyncio.run_coroutine_threadsafe(_put(), loop)
            fut.add_done_callback(_done)
        except Exception:
            logger.debug("trace schedule failed", exc_info=True)


def build_strands_tools(turn_state: StrandsTurnState) -> list:
    """Build tool callables bound to settings and turn-scoped result capture."""

    settings = get_settings()
    kb = KnowledgeBaseRetriever(settings)

    @tool
    def retrieve_kb_context(query: str) -> str:
        """
        Search the Smart Report Analyst knowledge base for database metadata (tables, columns)
        and historical SQL examples. Call this before writing SQL when schema or similar queries matter.

        Args:
            query: Natural language search string (e.g. user question or table/column hints).

        Returns:
            Concatenated retrieval passages for the model to use.
        """
        t0 = _now_ms()
        turn_state.emit_trace_sync(
            TraceKind.STEP_STARTED, {"step_name": "tool:retrieve_kb_context"}
        )
        turn_state.emit_trace_sync(
            TraceKind.REASONING_LINE, {"text": "Searching the knowledge base for schema and examples…"}
        )
        try:
            return kb.retrieve(query)
        finally:
            turn_state.emit_trace_sync(
                TraceKind.STEP_FINISHED, {"step_name": "tool:retrieve_kb_context"}
            )
            dt = _now_ms() - t0
            if dt >= 0:
                turn_state.emit_trace_sync(
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
        await turn_state.emit_trace_async(
            TraceKind.STEP_STARTED, {"step_name": "tool:execute_sql"}
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
                TraceKind.STEP_FINISHED, {"step_name": "tool:execute_sql"}
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
