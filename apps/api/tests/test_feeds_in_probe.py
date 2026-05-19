"""Tests for MH-MON-02 feeds-in probes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.services import health_registry as hr
from app.services.feeds_in_probe import (
    IBKR_MARKET_DATA_PROBE_NAME,
    POLYGON_PROBE_NAME,
    register_feeds_in_probes,
    _ibkr_market_data_gateway_probe,
    _polygon_provider_probe,
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
    saved_polygon = settings.polygon_api_key
    saved_gateway = settings.ibkr_gateway_url
    try:
        yield settings
    finally:
        settings.polygon_api_key = saved_polygon
        settings.ibkr_gateway_url = saved_gateway


def test_register_idempotent():
    register_feeds_in_probes()
    register_feeds_in_probes()
    assert POLYGON_PROBE_NAME in hr.list_registered()
    assert IBKR_MARKET_DATA_PROBE_NAME in hr.list_registered()


def test_polygon_probe_ok_when_key_configured(_restore_settings):
    _restore_settings.polygon_api_key = "test-key-123"
    result = _polygon_provider_probe()
    assert result.status == "ok"
    assert result.extra["configured"] is True


def test_polygon_probe_degraded_when_key_missing(_restore_settings):
    _restore_settings.polygon_api_key = ""
    result = _polygon_provider_probe()
    assert result.status == "degraded"
    assert result.extra["configured"] is False


def test_ibkr_md_probe_ok_when_url_set(_restore_settings):
    _restore_settings.ibkr_gateway_url = "https://localhost:5000/v1/api"
    result = _ibkr_market_data_gateway_probe()
    assert result.status == "ok"
    assert result.extra["configured"] is True
    assert result.extra["url"] == "https://localhost:5000/v1/api"


def test_ibkr_md_probe_degraded_when_url_blank(_restore_settings):
    _restore_settings.ibkr_gateway_url = ""
    result = _ibkr_market_data_gateway_probe()
    assert result.status == "degraded"
    assert result.extra["configured"] is False


def test_probes_appear_in_health_services_endpoint():
    client = TestClient(create_app())
    resp = client.get("/health/services")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["services"]]
    assert POLYGON_PROBE_NAME in names
    assert IBKR_MARKET_DATA_PROBE_NAME in names


def test_probes_never_make_network_calls(monkeypatch):
    """Sentinel: feeds-in probes must be config-only, no httpx/socket calls."""
    import socket

    def _boom(*a, **kw):
        raise AssertionError("feeds-in probe attempted a network call")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    # Neither probe should raise — they only read config.
    _polygon_provider_probe()
    _ibkr_market_data_gateway_probe()
