"""Tests for MH-MON-10 monitor dry-probe service."""

from __future__ import annotations

import time

import pytest

from app.services import health_registry as hr
from app.services.health_registry import ProbeResult, register_probe
from app.services.monitor_test_service import (
    MonitorDryProbeCooldownError,
    MonitorDryProbeError,
    MonitorDryProbeUnsupportedError,
    reset_monitor_test_cooldowns,
    run_operator_dry_probe,
)


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


def test_recursive_secret_scrubbing_removes_nested_keys():
    register_probe(
        "feeds_out.deep",
        lambda: ProbeResult(
            status="degraded",
            detail="bad authorization header",
            extra={
                "configured": False,
                "nested": {
                    "access_token": "abc",
                    "safe": "ok",
                    "list": [
                        {"refresh_token": "x"},
                        {"value": "Authorization failure"},
                    ],
                },
            },
        ),
    )

    result = run_operator_dry_probe("feeds_out.deep")
    assert "access_token" not in result.evidence.get("nested", {})
    assert result.evidence["nested"]["safe"] == "ok"
    assert "refresh_token" not in result.evidence["nested"]["list"][0]


def test_probe_exception_returns_down_not_crash():
    def _boom():
        raise RuntimeError("boom")

    register_probe("feeds_in.erroring", _boom)

    result = run_operator_dry_probe("feeds_in.erroring")
    assert result.status == "down"
    assert result.dry_probe is True
    assert "RuntimeError" not in result.message


def test_unsupported_service_is_rejected_even_if_registered():
    register_probe("runtime.synthetic", lambda: ProbeResult(status="ok", detail="ok"))
    with pytest.raises(MonitorDryProbeUnsupportedError):
        run_operator_dry_probe("runtime.synthetic")


def test_cooldown_blocks_repeated_probe_calls():
    register_probe("feeds_in.cooldown", lambda: ProbeResult(status="ok", detail="ok"))

    run_operator_dry_probe(
        "feeds_in.cooldown",
        cooldown_seconds=10.0,
        now_monotonic=100.0,
    )

    with pytest.raises(MonitorDryProbeCooldownError):
        run_operator_dry_probe(
            "feeds_in.cooldown",
            cooldown_seconds=10.0,
            now_monotonic=101.0,
        )


def test_probe_timeout_returns_safe_down_payload():
    def _slow_probe():
        time.sleep(0.05)
        return ProbeResult(status="ok", detail="slow")

    register_probe("feeds_in.slow", _slow_probe)
    result = run_operator_dry_probe(
        "feeds_in.slow",
        timeout_seconds=0.001,
        cooldown_seconds=0,
    )
    assert result.status == "down"
    assert result.dry_probe is True
    assert "timed out safely" in result.message.lower()
