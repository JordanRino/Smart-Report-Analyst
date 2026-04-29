"""tool_result shape vs PDF / report helpers."""

from smart_report_analyst.service.reports.manager import generate_pdf


def test_generate_pdf_accepts_normalized_tool_result():
    tool_result = {
        "refined_user_question": "Q",
        "executed_sql": "SELECT 1 AS x",
        "results": [{"x": 1}],
        "row_count": 1,
        "to_store": False,
    }
    buf = generate_pdf(tool_result, "user asked")
    assert buf.getvalue()[:4] == b"%PDF"
