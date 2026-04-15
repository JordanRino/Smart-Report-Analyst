"""Saved reports REST API (/api/reports/saved)."""

import uuid

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from smart_report_analyst.routes.routes import get_reports_store, router
from smart_report_analyst.service.reports.reports_store import ReportsStore


@pytest.fixture
def reports_client(tmp_path):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    store = ReportsStore(root=tmp_path)

    def _override() -> ReportsStore:
        return store

    app.dependency_overrides[get_reports_store] = _override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_saved_create_list_get_file_delete(reports_client: TestClient):
    res = reports_client.post(
        "/api/reports/saved",
        json={
            "executed_sql": "SELECT 1 AS n",
            "results": [{"n": 1}],
            "refined_user_question": "Saved title",
            "row_count": 1,
            "thread_id": "thread-a",
            "agent_id": "wlr_reporting_agent",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Saved title"
    assert data["thread_id"] == "thread-a"
    assert data["agent_id"] == "wlr_reporting_agent"
    assert data.get("main_agent_id") is None
    rid = data["id"]
    uuid.UUID(rid)

    lst = reports_client.get("/api/reports/saved")
    assert lst.status_code == 200
    body = lst.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert "results" not in body["items"][0]
    assert body["items"][0]["id"] == rid

    pdf = reports_client.get(f"/api/reports/saved/{rid}/file")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    dl = reports_client.delete(f"/api/reports/saved/{rid}")
    assert dl.status_code == 204

    assert reports_client.get(f"/api/reports/saved/{rid}/file").status_code == 404


def test_saved_invalid_uuid_returns_400(reports_client: TestClient):
    r = reports_client.get("/api/reports/saved/not-a-uuid/file")
    assert r.status_code == 400


def test_saved_create_persists_main_agent_id(reports_client: TestClient):
    res = reports_client.post(
        "/api/reports/saved",
        json={
            "executed_sql": "SELECT 1 AS n",
            "results": [{"n": 1}],
            "row_count": 1,
            "thread_id": "thread-orch",
            "agent_id": "sra_orchestrator_agent",
            "main_agent_id": "loan_report_analyst_agent",
        },
    )
    assert res.status_code == 201
    assert res.json().get("main_agent_id") == "loan_report_analyst_agent"
    lst = reports_client.get("/api/reports/saved").json()
    assert lst["items"][0]["main_agent_id"] == "loan_report_analyst_agent"


def test_saved_list_never_includes_results_array(reports_client: TestClient):
    reports_client.post(
        "/api/reports/saved",
        json={
            "query": "SELECT 2",
            "results": [{"x": 2}],
            "thread_id": "t1",
            "agent_id": "a1",
        },
    )
    lst = reports_client.get("/api/reports/saved").json()
    item = lst["items"][0]
    assert "results" not in item
    assert item["results_row_count"] == 1
