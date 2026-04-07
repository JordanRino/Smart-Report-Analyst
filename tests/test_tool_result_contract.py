"""tool_result shape vs PDF / report helpers."""

from smart_report_analyst.service.report_generation.manager import generate_pdf
from smart_report_analyst.ui.chainlit.utils.formatting import should_generate_report


def test_should_generate_report_with_normalized_tool_result():
    tool_result = {
        "refined_user_question": "Top banks",
        "executed_sql": "SELECT 1",
        "results": [{"Bank": "A"}],
        "row_count": 1,
        "to_store": True,
    }
    assert should_generate_report(tool_result) is True


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
