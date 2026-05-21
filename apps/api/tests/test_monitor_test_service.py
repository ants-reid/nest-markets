"""Tests for MH-MON-10 monitor dry-probe service."""

from __future__ import annotations

import pytest

from app.services import health_registry as hr
from app.services.health_registry import ProbeResult, register_probe
from app.services.monitor_test_service import MonitorDryProbeError, run_operator_dry_probe


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = dict(hr._REGISTRY)
    try:
        yield
    finally:
        hr._REGISTRY.clear()
        hr._REGISTRY.update(saved)


def test_unknown_service_is_rejected():
    with pytest.raises(MonitorDryProbeError):
        run_operator_dry_probe("not-registered")


def test_known_service_returns_dry_probe_payload():
    register_probe(
        "feeds_in.synthetic",
        lambda: ProbeResult(status="ok", detail="configured", extra={"configured": True}),
    )

    result = run_operator_dry_probe("feeds_in.synthetic")
    assert result.service_id == "feeds_in.synthetic"
    assert result.category == "feeds_in"
    assert result.status == "healthy"
    assert result.dry_probe is True
    assert result.evidence["configured"] is True


def test_secret_like_fields_are_removed_from_evidence():
    register_probe(
        "feeds_out.synthetic",
        lambda: ProbeResult(
            status="degraded",
            detail="missing key",
            extra={
                "configured": False,
                "api_key": "do-not-return",
                "token": "do-not-return",
            },
        ),
    )

    result = run_operator_dry_probe("feeds_out.synthetic")
    assert result.status == "degraded"
    assert "api_key" not in result.evidence
    assert "token" not in result.evidence
    assert result.evidence["configured"] is False


def test_probe_exception_returns_down_not_crash():
    def _boom():
        raise RuntimeError("boom")

    register_probe("infrastructure.synthetic", _boom)

    result = run_operator_dry_probe("infrastructure.synthetic")
    assert result.status == "down"
    assert result.dry_probe is True
    assert "RuntimeError" in result.message
