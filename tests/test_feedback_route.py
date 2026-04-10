"""POST /api/feedback/positive."""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from smart_report_analyst.routes.routes import router
from smart_report_analyst.service.feedback import snapshot_index as snapshot_index_mod


@pytest.fixture
def feedback_client(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def fake_handle(payload: dict):
        fake_handle.last = payload
        return {"status": "success"}

    monkeypatch.setattr(
        "smart_report_analyst.routes.routes.handle_positive_feedback",
        fake_handle,
    )
    return TestClient(app), fake_handle


def test_feedback_positive_rejects_ambiguous_body(feedback_client):
    client, _ = feedback_client
    res = client.post("/api/feedback/positive", json={})
    assert res.status_code == 422


def test_feedback_positive_direct_body(feedback_client):
    client, fake = feedback_client
    res = client.post(
        "/api/feedback/positive",
        json={
            "refined_user_question": "Top lenders",
            "executed_sql": "SELECT 1",
            "to_store": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert fake.last == {
        "refined_user_question": "Top lenders",
        "executed_sql": "SELECT 1",
        "to_store": True,
    }


def test_feedback_positive_by_message_id(feedback_client, monkeypatch):
    client, fake = feedback_client
    monkeypatch.setattr(snapshot_index_mod, "_store", {})

    snapshot_index_mod.register_feedback_snapshot(
        "thread-1",
        "msg-1",
        {
            "refined_user_question": "Q",
            "executed_sql": "SELECT 2",
            "to_store": False,
        },
    )
    res = client.post(
        "/api/feedback/positive",
        json={"thread_id": "thread-1", "message_id": "msg-1"},
    )
    assert res.status_code == 200
    assert fake.last["refined_user_question"] == "Q"
    assert fake.last["executed_sql"] == "SELECT 2"
    assert fake.last["to_store"] is False


def test_feedback_positive_unknown_message(feedback_client):
    client, _ = feedback_client
    res = client.post(
        "/api/feedback/positive",
        json={"thread_id": "t", "message_id": "missing"},
    )
    assert res.status_code == 404
