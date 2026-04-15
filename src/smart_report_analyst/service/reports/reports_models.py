"""HTTP request models for saved items (records + reports)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from smart_report_analyst.service.reports.report_pdf import ReportPdfRequest


class ReportSaveRequest(ReportPdfRequest):
    """POST body: PDF payload plus thread/agent attribution."""

    thread_id: str = Field(min_length=1)
    agent_id: str = Field(
        min_length=1,
        description="CopilotKit agent id (e.g. wlr_reporting_agent, sra_orchestrator_agent).",
    )
    title: str | None = None
    source_message_id: str | None = None
    main_agent_id: str | None = Field(
        default=None,
        description="When agent_id is the orchestrator, properties.mainAgentId (data specialist).",
    )


class RecordSaveRequest(BaseModel):
    """POST /api/records/saved — save raw SQL results as a CSV record."""

    results: list[Any] = Field(default_factory=list)
    executed_sql: str = ""
    refined_user_question: str | None = None
    row_count: int | None = None
    thread_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    title: str | None = None
    source_message_id: str | None = None
    main_agent_id: str | None = None
