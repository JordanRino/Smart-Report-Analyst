from __future__ import annotations

import io
from typing import Any, Mapping
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_pdf(tool_result: Mapping[str, Any], user_question: str) -> io.BytesIO:
    """Build a simple PDF from normalized ``execute_sql`` tool_result and fallback title."""
    title = tool_result.get("refined_user_question") or user_question
    results = tool_result.get("results") or []
    sql_query = tool_result.get("executed_sql") or ""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    elements: list = []

    # Title
    elements.append(Paragraph(f"<b>{escape(str(title))}</b>", styles["Title"]))
    elements.append(Spacer(1, 20))

    # Table
    if results:
        df = pd.DataFrame(results)

        data = [df.columns.tolist()] + df.values.tolist()
        table = Table(data, repeatRows=1)

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))

    # SQL
    elements.append(Paragraph("<b>SQL Query</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(Preformatted(sql_query or "(none)", styles["Code"]))

    doc.build(elements)

    buffer.seek(0)
    return buffer
