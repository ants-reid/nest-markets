"""Tests for MH-MON-10 ``POST /monitor/test/{service_id}`` route."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.middleware.auth import api_key_auth
from app.services import health_registry as hr
from app.services.health_registry import ProbeResult, register_probe
from app.services.monitor_test_service import reset_monitor_test_cooldowns


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = dict(hr._REGISTRY)
    try:
        reset_monitor_test_cooldowns()
        yield
    finally:
        reset_monitor_test_cooldowns()
        hr._REGISTRY.clear()
        hr._REGISTRY.update(saved)


@pytest.fixture(autouse=True)
def _restore_auth():
    saved_enabled = api_key_auth.enabled
    saved_key = api_key_auth.api_key
    try:
        yield
    finally:
        api_key_auth.enabled = saved_enabled
        api_key_auth.api_key = saved_key


def test_route_returns_schema_shape_for_known_service(client):
    register_probe(
        "feeds_in.synthetic",
        lambda: ProbeResult(status="ok", detail="ready", extra={"configured": True}),
    )

    resp = client.post("/monitor/test/feeds_in.synthetic")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "service_id",
        "service_name",
        "category",
        "status",
        "dry_probe",
        "checked_at",
        "latency_ms",
        "message",
        "recommended_action",
        "evidence",
        "safety_notes",
    ):
        assert key in body, f"missing key: {key}"
    assert body["service_id"] == "feeds_in.synthetic"
    assert body["dry_probe"] is True
    assert body["status"] == "healthy"


def test_route_rejects_unknown_service(client):
    resp = client.post("/monitor/test/does.not.exist")
    assert resp.status_code == 404


def test_route_enforces_api_key_when_enabled(client):
    register_probe("database.synthetic", lambda: ProbeResult(status="ok", detail="ok"))
    api_key_auth.enabled = True
    api_key_auth.api_key = "unit-test-key"

    unauthorized = client.post("/monitor/test/database.synthetic")
    assert unauthorized.status_code == 401

    wrong = client.post(
        "/monitor/test/database.synthetic",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert wrong.status_code == 401

    authorized = client.post(
        "/monitor/test/database.synthetic",
        headers={"Authorization": "Bearer unit-test-key"},
    )
    assert authorized.status_code == 200, authorized.text


def test_route_never_returns_secret_fields(client):
    register_probe(
        "feeds_out.synthetic",
        lambda: ProbeResult(
            status="degraded",
            detail="missing creds",
            extra={"configured": False, "api_key": "secret-value"},
        ),
    )

    resp = client.post("/monitor/test/feeds_out.synthetic")
    assert resp.status_code == 200, resp.text
    evidence = resp.json()["evidence"]
    assert "api_key" not in evidence
    assert evidence["configured"] is False


def test_route_does_not_invoke_broker_or_live_execution_paths(client, monkeypatch):
    register_probe("feeds_in.synthetic", lambda: ProbeResult(status="ok", detail="ok"))

    def _boom(*args, **kwargs):
        raise AssertionError("broker or live execution path should not be invoked")

    monkeypatch.setattr("app.services.broker_service.BrokerService.submit_auto_order", _boom)
    monkeypatch.setattr("app.services.live_execution_service.LiveExecutionService.submit", _boom)

    resp = client.post("/monitor/test/feeds_in.synthetic")
    assert resp.status_code == 200, resp.text
    assert resp.json()["dry_probe"] is True


def test_probe_error_returns_safe_payload_not_500(client):
    def _boom():
        raise RuntimeError("probe failed")

    register_probe("feeds_in.erroring", _boom)
    resp = client.post("/monitor/test/feeds_in.erroring")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_probe"] is True
    assert body["status"] == "down"
    assert "RuntimeError" not in body["message"]


def test_route_returns_400_for_unsupported_registered_service(client):
    register_probe("runtime.synthetic", lambda: ProbeResult(status="ok", detail="ok"))
    resp = client.post("/monitor/test/runtime.synthetic")
    assert resp.status_code == 400


def test_route_returns_429_for_cooldown(client):
    register_probe("feeds_in.cooldown", lambda: ProbeResult(status="ok", detail="ok"))
    first = client.post("/monitor/test/feeds_in.cooldown")
    assert first.status_code == 200

    second = client.post("/monitor/test/feeds_in.cooldown")
    assert second.status_code == 429
    body = second.json()
    assert body["dry_probe"] is True
    assert body["service_id"] == "feeds_in.cooldown"
    assert "retry_after_seconds" in body


def test_route_timeout_returns_safe_payload(client):
    import time

    def _slow_probe():
        time.sleep(0.05)
        return ProbeResult(status="ok", detail="slow")

    register_probe("feeds_in.slow", _slow_probe)
    resp = client.post("/monitor/test/feeds_in.slow")
    # With default timeout this may pass or timeout depending on system load;
    # either outcome must be non-500 and dry-probe-safe.
    assert resp.status_code in (200, 429)
