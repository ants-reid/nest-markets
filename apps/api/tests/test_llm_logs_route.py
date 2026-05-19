"""MH-COCKPIT-04-API — Tests for /llm-logs/recent."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.models.llm_request_log import LLMRequestLog
from app.db.session import SessionLocal
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def _insert(session, **kwargs) -> LLMRequestLog:
    defaults = dict(
        provider="openai",
        model_requested="gpt-test",
        system_prompt_preview="sys",
        user_prompt_preview="user",
    )
    defaults.update(kwargs)
    row = LLMRequestLog(**defaults)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@pytest.fixture(autouse=True)
def _clean_table():
    s = SessionLocal()
    try:
        s.query(LLMRequestLog).filter(
            LLMRequestLog.provider.in_(["test-cockpit-04", "test-cockpit-04-other"])
        ).delete(synchronize_session=False)
        s.commit()
    finally:
        s.close()
    yield
    s = SessionLocal()
    try:
        s.query(LLMRequestLog).filter(
            LLMRequestLog.provider.in_(["test-cockpit-04", "test-cockpit-04-other"])
        ).delete(synchronize_session=False)
        s.commit()
    finally:
        s.close()


def test_endpoint_returns_recent_rows_newest_first(client):
    s = SessionLocal()
    try:
        for i in range(3):
            _insert(
                s,
                provider="test-cockpit-04",
                model_requested=f"m-{i}",
                user_prompt_preview=f"prompt-{i}",
            )
    finally:
        s.close()

    resp = client.get("/llm-logs/recent?provider=test-cockpit-04")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    models = [item["model_requested"] for item in body["items"]]
    # Newest first → latest insert is m-2
    assert models == ["m-2", "m-1", "m-0"]


def test_filter_by_provider(client):
    s = SessionLocal()
    try:
        _insert(s, provider="test-cockpit-04", user_prompt_preview="a")
        _insert(s, provider="test-cockpit-04-other", user_prompt_preview="b")
    finally:
        s.close()

    resp = client.get("/llm-logs/recent?provider=test-cockpit-04-other")
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["provider"] == "test-cockpit-04-other"


def test_filter_by_correlation_id(client):
    s = SessionLocal()
    try:
        _insert(s, provider="test-cockpit-04", correlation_id="corr-1", user_prompt_preview="a")
        _insert(s, provider="test-cockpit-04", correlation_id="corr-2", user_prompt_preview="b")
    finally:
        s.close()

    resp = client.get("/llm-logs/recent?correlation_id=corr-1")
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["correlation_id"] == "corr-1"


def test_only_errors_filter(client):
    s = SessionLocal()
    try:
        _insert(s, provider="test-cockpit-04", user_prompt_preview="ok-row")
        _insert(
            s,
            provider="test-cockpit-04",
            user_prompt_preview="bad-row",
            error_class="TimeoutError",
            error_message="took too long",
        )
    finally:
        s.close()

    resp = client.get("/llm-logs/recent?provider=test-cockpit-04&only_errors=true")
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["error_class"] == "TimeoutError"


def test_limit_enforced(client):
    s = SessionLocal()
    try:
        for i in range(5):
            _insert(s, provider="test-cockpit-04", user_prompt_preview=f"p-{i}")
    finally:
        s.close()

    resp = client.get("/llm-logs/recent?provider=test-cockpit-04&limit=2")
    body = resp.json()
    assert body["count"] == 2
    assert body["limit"] == 2


def test_invalid_limit_rejected(client):
    resp = client.get("/llm-logs/recent?limit=0")
    assert resp.status_code == 422
    resp = client.get("/llm-logs/recent?limit=99999")
    assert resp.status_code == 422


def test_long_preview_is_capped(client):
    s = SessionLocal()
    try:
        _insert(
            s,
            provider="test-cockpit-04",
            user_prompt_preview="x" * 5000,
        )
    finally:
        s.close()

    resp = client.get("/llm-logs/recent?provider=test-cockpit-04&limit=1")
    body = resp.json()
    preview = body["items"][0]["user_prompt_preview"]
    assert preview is not None
    assert len(preview) <= 1100  # 1000 cap + "...[truncated]"
    assert preview.endswith("[truncated]")


def test_response_payload_serialized_safely(client):
    s = SessionLocal()
    try:
        _insert(
            s,
            provider="test-cockpit-04",
            user_prompt_preview="p",
            response_payload_json={"choices": [{"message": {"content": "hello"}}]},
        )
    finally:
        s.close()

    resp = client.get("/llm-logs/recent?provider=test-cockpit-04&limit=1")
    item = resp.json()["items"][0]
    assert item["response_payload_preview"] is not None
    assert "hello" in item["response_payload_preview"]
