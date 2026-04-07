"""Document required keys for Strands direct-invoke SQL Lambda JSON (see lambda_function_execute_sql_strands)."""

from __future__ import annotations

SUCCESS_KEYS = frozenset(
    {"refined_user_question", "executed_sql", "results", "row_count", "to_store"}
)
ERROR_KEYS = frozenset(
    {
        "error",
        "message",
        "refined_user_question",
        "executed_sql",
        "results",
        "row_count",
        "to_store",
    }
)


def test_success_shape_matches_strands_lambda():
    body = {
        "refined_user_question": "Count loans",
        "executed_sql": "SELECT 1",
        "results": [{"n": 1}],
        "row_count": 1,
        "to_store": True,
    }
    assert SUCCESS_KEYS == set(body.keys())
    assert "error" not in body


def test_error_shape_missing_query():
    body = {
        "error": True,
        "message": "Missing or empty 'query'",
        "refined_user_question": None,
        "executed_sql": None,
        "results": [],
        "row_count": 0,
        "to_store": False,
    }
    assert ERROR_KEYS == set(body.keys())


def test_error_shape_db_exception():
    body = {
        "error": True,
        "message": "syntax error",
        "refined_user_question": "Q",
        "executed_sql": "SELECT oops",
        "results": [],
        "row_count": 0,
        "to_store": False,
    }
    assert ERROR_KEYS == set(body.keys())
