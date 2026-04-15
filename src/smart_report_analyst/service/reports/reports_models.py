"""HTTP request models for saved SQL reports (dashboard library)."""

from __future__ import annotations

from pydantic import Field

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
