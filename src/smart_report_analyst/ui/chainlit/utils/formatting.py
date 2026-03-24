"""Formatting helpers for Chainlit UI."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict


def to_title(question: str) -> str:
    """Turn a question into a clean title."""
    text = (question or "").strip()
    if not text:
        return "SBA Loan Report"

    text = re.sub(r"\s+", " ", text)
    text = text.rstrip("?.! ")
    return text[:1].upper() + text[1:]


def slugify(text: str, max_length: int = 60) -> str:
    """Create a safe filename slug."""
    cleaned = (text or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned[:max_length] or "report"


def build_report_filename(question: str) -> str:
    """Build a nice PDF filename from the user question."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{slugify(question)}_{stamp}.pdf"


def should_generate_report(tool_result: Dict[str, Any] | None) -> bool:
    """Return True when the query produced a tabular result worth exporting."""
    if not tool_result:
        return False

    row_count = tool_result.get("row_count", 0)
    results = tool_result.get("results", [])

    return bool(row_count and row_count > 0 and results)


def format_sql_block(sql: str) -> str:
    """Format SQL as a Markdown code block."""
    sql = (sql or "").strip()
    if not sql:
        return ""
    return f"```sql\n{sql}\n```"