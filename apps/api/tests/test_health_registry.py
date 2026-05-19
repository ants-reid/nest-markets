"""Tests for MH-MON-01 health endpoint registry."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import health_registry as hr
from app.services.health_registry import (
    ProbeResult,
    list_registered,
    register_probe,
    snapshot,
    unregister_probe,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Snapshot/restore the global registry around each test."""
    saved = dict(hr._REGISTRY)
    try:
        yield
    finally:
        hr._REGISTRY.clear()
        hr._REGISTRY.update(saved)


def test_register_and_list_probe():
    register_probe("synth_ok", lambda: ProbeResult(status="ok", detail="alive"))
    assert "synth_ok" in list_registered()


def test_unregister_probe():
    register_probe("temp", lambda: ProbeResult(status="ok"))
    unregister_probe("temp")
    assert "temp" not in list_registered()


def test_unregister_unknown_is_noop():
    unregister_probe("does_not_exist")  # must not raise


def test_register_rejects_empty_name():
    with pytest.raises(ValueError):
        register_probe("", lambda: ProbeResult(status="ok"))


def test_register_rejects_non_callable():
    with pytest.raises(TypeError):
        register_probe("bad", "not callable")  # type: ignore[arg-type]


def test_snapshot_runs_each_probe_once():
    counter = {"n": 0}

    def probe():
        counter["n"] += 1
        return ProbeResult(status="ok")

    # Replace the auto-registered defaults so we count only our probe.
    hr._REGISTRY.clear()
    register_probe("counted", probe)
    rows = snapshot()
    assert counter["n"] == 1
    assert len(rows) == 1
    assert rows[0].name == "counted"
    assert rows[0].status == "ok"
    assert rows[0].latency_ms is not None


def test_snapshot_catches_probe_exceptions():
    hr._REGISTRY.clear()

    def boom():
        raise RuntimeError("kaboom")

    register_probe("explosive", boom)
    rows = snapshot()
    assert len(rows) == 1
    assert rows[0].status == "error"
    assert "RuntimeError" in (rows[0].detail or "")


def test_snapshot_handles_bad_return_type():
    hr._REGISTRY.clear()
    register_probe("wrong_type", lambda: "not a ProbeResult")  # type: ignore[arg-type, return-value]
    rows = snapshot()
    assert rows[0].status == "error"
    assert "ProbeResult" in (rows[0].detail or "")


def test_snapshot_sorted_by_name():
    hr._REGISTRY.clear()
    register_probe("zebra", lambda: ProbeResult(status="ok"))
    register_probe("alpha", lambda: ProbeResult(status="ok"))
    register_probe("mike", lambda: ProbeResult(status="ok"))
    names = [r.name for r in snapshot()]
    assert names == ["alpha", "mike", "zebra"]


def test_health_services_endpoint_overall_ok(monkeypatch):
    hr._REGISTRY.clear()
    register_probe("synth", lambda: ProbeResult(status="ok"))
    client = TestClient(create_app())
    resp = client.get("/health/services")
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall"] == "ok"
    assert "synth" in body["registered"]
    assert any(s["name"] == "synth" for s in body["services"])


def test_health_services_endpoint_overall_down_on_error_probe():
    hr._REGISTRY.clear()
    register_probe("ok_one", lambda: ProbeResult(status="ok"))
    register_probe("dead", lambda: (_ for _ in ()).throw(RuntimeError("dead")))
    client = TestClient(create_app())
    resp = client.get("/health/services")
    assert resp.status_code == 200
    assert resp.json()["overall"] == "down"


def test_health_services_endpoint_overall_degraded():
    hr._REGISTRY.clear()
    register_probe("a", lambda: ProbeResult(status="ok"))
    register_probe("b", lambda: ProbeResult(status="degraded", detail="slow"))
    client = TestClient(create_app())
    resp = client.get("/health/services")
    assert resp.json()["overall"] == "degraded"


def test_root_health_endpoint_unchanged():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
