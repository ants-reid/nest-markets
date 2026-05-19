"""Tests for MH-MON-03 feeds-out probes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services import health_registry as hr
from app.services.feeds_out_probe import (
    IBKR_ORDER_PROBE_NAME,
    OPENAI_PROBE_NAME,
    register_feeds_out_probes,
    _ibkr_order_gateway_probe,
    _openai_provider_probe,
)


@pytest.fixture(autouse=True)
def _restore_registry():
    saved = dict(hr._REGISTRY)
    try:
        yield
    finally:
        hr._REGISTRY.clear()
        hr._REGISTRY.update(saved)


@pytest.fixture(autouse=True)
def _restore_settings():
    settings = get_settings()
    saved_openai = settings.openai_api_key
    saved_gateway = settings.ibkr_gateway_url
    try:
        yield settings
    finally:
        settings.openai_api_key = saved_openai
        settings.ibkr_gateway_url = saved_gateway


def test_register_idempotent():
    register_feeds_out_probes()
    register_feeds_out_probes()
    assert OPENAI_PROBE_NAME in hr.list_registered()
    assert IBKR_ORDER_PROBE_NAME in hr.list_registered()


def test_openai_probe_ok(_restore_settings):
    _restore_settings.openai_api_key = "sk-test"
    r = _openai_provider_probe()
    assert r.status == "ok"
    assert r.extra["configured"] is True


def test_openai_probe_degraded(_restore_settings):
    _restore_settings.openai_api_key = ""
    r = _openai_provider_probe()
    assert r.status == "degraded"


def test_ibkr_order_probe_reports_drift_lock(_restore_settings):
    _restore_settings.ibkr_gateway_url = "https://localhost:5000/v1/api"
    r = _ibkr_order_gateway_probe()
    assert r.status == "ok"
    # Drift lock posture must be exposed and must be False.
    assert r.extra["auto_trading_enabled"] is False
    assert r.extra["live_trading_enabled"] is False


def test_ibkr_order_probe_degraded_when_url_blank(_restore_settings):
    _restore_settings.ibkr_gateway_url = ""
    r = _ibkr_order_gateway_probe()
    assert r.status == "degraded"
    # Drift-lock posture is reported even when URL is blank.
    assert r.extra["auto_trading_enabled"] is False
    assert r.extra["live_trading_enabled"] is False


def test_probes_appear_in_health_services_endpoint():
    client = TestClient(create_app())
    body = client.get("/health/services").json()
    names = [s["name"] for s in body["services"]]
    assert OPENAI_PROBE_NAME in names
    assert IBKR_ORDER_PROBE_NAME in names


def test_probes_do_not_call_submission_paths(monkeypatch):
    """Sentinel: feeds-out probes must not invoke any broker submission code."""
    import app.services.broker_service as broker_service_mod

    def _boom(*a, **kw):
        raise AssertionError("feeds-out probe invoked BrokerService submission path")

    if hasattr(broker_service_mod, "BrokerService"):
        monkeypatch.setattr(
            broker_service_mod.BrokerService, "__init__", _boom, raising=False
        )
    _openai_provider_probe()
    _ibkr_order_gateway_probe()
