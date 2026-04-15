"""Request model and orchestration for SQL-result PDF generation (used by HTTP layer)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from smart_report_analyst.service.reports.manager import generate_pdf

# Guardrails for request size / memory (Copilot passes result rows in JSON).
MAX_RESULT_ROWS = 10_000
MAX_FALLBACK_TITLE_LEN = 200


class ReportPdfClientError(Exception):
    """Invalid PDF request (HTTP 400)."""


class ReportPdfServerError(Exception):
    """PDF build failed (HTTP 500)."""


class ReportPdfRequest(BaseModel):
    """Body aligned with normalized ``execute_sql`` tool result + PDF title hints."""

    executed_sql: str = ""
    results: list[Any] = Field(default_factory=list)
    refined_user_question: str | None = None
    row_count: int | None = None
    fallback_title: str | None = Field(default=None, alias="fallbackTitle")
    error: bool | None = None
    # Frontend may still send ``query`` from Copilot action args.
    query: str | None = None

    model_config = {"populate_by_name": True}

    @field_validator("results", mode="before")
    @classmethod
    def results_must_be_list(cls, v: Any) -> list[Any]:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        raise ValueError("results must be a list")

    def to_tool_result(self) -> dict[str, Any]:
        sql = self.executed_sql.strip() or (self.query or "").strip()
        out: dict[str, Any] = {
            "executed_sql": sql,
            "results": self.results,
            "refined_user_question": self.refined_user_question,
        }
        if self.row_count is not None:
            out["row_count"] = self.row_count
        return out

    def fallback_user_question(self) -> str:
        if self.fallback_title and self.fallback_title.strip():
            return self.fallback_title.strip()[:MAX_FALLBACK_TITLE_LEN]
        return "SBA loan analysis report"


def _safe_filename_fragment(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", title.strip())[:60].strip("-")
    return slug or "report"


def render_sql_report_pdf(body: ReportPdfRequest) -> tuple[bytes, str]:
    """
    Validate body, render PDF, return raw bytes and ``Content-Disposition`` value.

    Raises:
        ReportPdfClientError: business validation failed.
        ReportPdfServerError: PDF engine failed.
    """
    if body.error is True:
        raise ReportPdfClientError("Cannot generate PDF for failed SQL execution")

    if len(body.results) > MAX_RESULT_ROWS:
        raise ReportPdfClientError(f"Too many rows (max {MAX_RESULT_ROWS})")

    tool_result = body.to_tool_result()
    try:
        buffer = generate_pdf(tool_result, body.fallback_user_question())
    except Exception as exc:  # pylint: disable=broad-except
        raise ReportPdfServerError(f"PDF generation failed: {exc}") from exc

    raw_title = tool_result.get("refined_user_question") or body.fallback_user_question()
    safe_title = _safe_filename_fragment(str(raw_title))
    filename = f"{safe_title}.pdf"
    ascii_filename = filename.encode("ascii", "ignore").decode("ascii") or "report.pdf"
    content_disp = f'attachment; filename="{ascii_filename}"'

    return buffer.getvalue(), content_disp
