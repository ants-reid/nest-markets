"""Tests for MH-158-A ``GET /monitor/worker-run-log/overview`` route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_overview_snapshot_shape():
    client = TestClient(app)
    resp = client.get("/monitor/worker-run-log/overview?limit=5")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in ("advisory", "limit", "retention", "totals", "entries"):
        assert key in body, f"missing key: {key}"
    assert body["limit"] == 5
    # retention should be a dict with the well-known keys from the existing
    # WorkerRunLogService.get_retention_metadata() implementation.
    for key in (
        "storage_backend",
        "max_entries",
        "current_entry_count",
        "utilization_pct",
        "near_capacity",
        "retention_status",
    ):
        assert key in body["retention"], f"missing retention key: {key}"


def test_overview_invalid_limit_rejected_at_route():
    client = TestClient(app)
    resp = client.get("/monitor/worker-run-log/overview?limit=0")
    # FastAPI Query validator rejects with 422
    assert resp.status_code == 422
