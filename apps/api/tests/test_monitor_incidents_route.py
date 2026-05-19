"""Tests for MH-MON-05 monitor/incidents route."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.models.incident_log import IncidentLog
from app.db.session import SessionLocal
from app.main import create_app
from app.services.incident_log_service import record_incident


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _clean_table():
    s = SessionLocal()
    try:
        s.query(IncidentLog).delete()
        s.commit()
    finally:
        s.close()
    yield
    s = SessionLocal()
    try:
        s.query(IncidentLog).delete()
        s.commit()
    finally:
        s.close()


def test_get_incidents_empty(client):
    resp = client.get("/monitor/incidents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["incidents"] == []


def test_get_incidents_returns_recent(client):
    s = SessionLocal()
    try:
        record_incident(s, severity="info", code="a", title="one", source="x")
        record_incident(s, severity="warn", code="b", title="two", source="x")
        s.commit()
    finally:
        s.close()

    resp = client.get("/monitor/incidents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    titles = [i["title"] for i in body["incidents"]]
    assert titles == ["two", "one"]


def test_get_incidents_filter_severity(client):
    s = SessionLocal()
    try:
        record_incident(s, severity="info", code="a", title="i", source="x")
        record_incident(s, severity="error", code="b", title="e", source="x")
        s.commit()
    finally:
        s.close()

    resp = client.get("/monitor/incidents?severity=error")
    body = resp.json()
    assert body["count"] == 1
    assert body["incidents"][0]["severity"] == "error"


def test_get_incidents_invalid_severity_400(client):
    resp = client.get("/monitor/incidents?severity=fatal")
    assert resp.status_code == 400


def test_get_incidents_limit_validation(client):
    resp = client.get("/monitor/incidents?limit=0")
    assert resp.status_code == 422
    resp = client.get("/monitor/incidents?limit=501")
    assert resp.status_code == 422


def test_no_post_endpoint_for_incidents(client):
    """MH-MON-05 is read-only over HTTP. Writes must come from backend services."""
    resp = client.post("/monitor/incidents", json={"severity": "info"})
    assert resp.status_code in (404, 405)
