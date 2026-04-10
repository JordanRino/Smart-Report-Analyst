"""POST /api/reports/pdf."""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from smart_report_analyst.routes.routes import router


@pytest.fixture
def pdf_client():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_reports_pdf_returns_valid_pdf(pdf_client):
    res = pdf_client.post(
        "/api/reports/pdf",
        json={
            "executed_sql": "SELECT 1 AS x",
            "results": [{"x": 1}],
            "refined_user_question": "Unit test question",
            "row_count": 1,
        },
    )
    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("content-type", "")
    assert res.content[:4] == b"%PDF"
    assert "attachment" in res.headers.get("content-disposition", "")


def test_reports_pdf_accepts_query_alias(pdf_client):
    res = pdf_client.post(
        "/api/reports/pdf",
        json={
            "query": "SELECT 2 AS y",
            "results": [{"y": 2}],
        },
    )
    assert res.status_code == 200
    assert res.content[:4] == b"%PDF"


def test_reports_pdf_rejects_error_execution(pdf_client):
    res = pdf_client.post(
        "/api/reports/pdf",
        json={
            "error": True,
            "executed_sql": "SELECT 1",
            "results": [],
        },
    )
    assert res.status_code == 400


def test_reports_pdf_rejects_too_many_rows(pdf_client):
    res = pdf_client.post(
        "/api/reports/pdf",
        json={
            "executed_sql": "SELECT 1",
            "results": [{"a": i} for i in range(10_001)],
        },
    )
    assert res.status_code == 400
