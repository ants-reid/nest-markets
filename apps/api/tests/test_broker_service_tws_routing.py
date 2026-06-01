"""BrokerService adapter-selection tests (TWS routing guard).

These tests verify that ``BrokerService.ensure_connected`` keeps the
default CP Gateway path unchanged and only switches to the TWS socket
adapter when ``BROKER_PROVIDER=tws[_socket]`` AND ``TWS_ENABLED=true``.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.clients.broker.ibkr_adapter import IBKRAdapter
from app.clients.broker.tws_adapter import TwsBroker
from app.services.broker_service import BrokerService


def _patched_settings(**overrides):
    base = {
        "broker_provider": "ibkr",
        "tws_enabled": False,
        "tws_host": "127.0.0.1",
        "tws_port": 4002,
        "tws_client_id": 43,
        "ibkr_gateway_url": "https://localhost:5000/v1/api",
        "ibkr_account_id": "DUP1",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_default_provider_uses_ibkr_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.broker_service.get_settings",
        lambda: _patched_settings(),
    )
    captured: dict = {}

    def fake_create(broker_type, **kwargs):
        captured["broker_type"] = broker_type
        captured["kwargs"] = kwargs
        return MagicMock(spec=IBKRAdapter)

    monkeypatch.setattr(
        "app.services.broker_service.BrokerGatewayFactory.create",
        staticmethod(fake_create),
    )

    svc = BrokerService()
    await svc.ensure_connected()

    assert captured["broker_type"] == "ibkr"
    assert captured["kwargs"]["base_url"] == "https://localhost:5000/v1/api"
    assert captured["kwargs"]["preferred_account_id"] == "DUP1"
    assert "tws_submit_enabled" not in captured["kwargs"]


@pytest.mark.asyncio
async def test_tws_provider_requires_tws_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.broker_service.get_settings",
        lambda: _patched_settings(broker_provider="tws", tws_enabled=False),
    )
    svc = BrokerService()
    with pytest.raises(RuntimeError, match="TWS_ENABLED"):
        await svc.ensure_connected()


@pytest.mark.asyncio
async def test_tws_provider_selects_tws_adapter_with_submit_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.broker_service.get_settings",
        lambda: _patched_settings(broker_provider="tws", tws_enabled=True),
    )
    monkeypatch.setattr(
        "app.services.broker_service.get_broker_mode_metadata",
        lambda: {
            "broker": "ibkr",
            "mode": "paper",
            "paper_trading_enabled": True,
            "live_execution_enabled": False,
        },
    )
    captured: dict = {}

    def fake_create(broker_type, **kwargs):
        captured["broker_type"] = broker_type
        captured["kwargs"] = kwargs
        return MagicMock(spec=TwsBroker)

    monkeypatch.setattr(
        "app.services.broker_service.BrokerGatewayFactory.create",
        staticmethod(fake_create),
    )

    svc = BrokerService()
    await svc.ensure_connected()

    assert captured["broker_type"] == "tws"
    assert captured["kwargs"]["tws_submit_enabled"] is True
    assert captured["kwargs"]["tws_host"] == "127.0.0.1"
    assert captured["kwargs"]["tws_port"] == 4002
    assert captured["kwargs"]["tws_client_id"] == 43
    assert captured["kwargs"]["preferred_account_id"] == "DUP1"


@pytest.mark.asyncio
async def test_tws_submit_disabled_when_live_execution_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.broker_service.get_settings",
        lambda: _patched_settings(broker_provider="tws_socket", tws_enabled=True),
    )
    monkeypatch.setattr(
        "app.services.broker_service.get_broker_mode_metadata",
        lambda: {
            "broker": "ibkr",
            "mode": "live",
            "paper_trading_enabled": False,
            "live_execution_enabled": True,
        },
    )
    captured: dict = {}

    def fake_create(broker_type, **kwargs):
        captured["broker_type"] = broker_type
        captured["kwargs"] = kwargs
        return MagicMock(spec=TwsBroker)

    monkeypatch.setattr(
        "app.services.broker_service.BrokerGatewayFactory.create",
        staticmethod(fake_create),
    )

    svc = BrokerService()
    await svc.ensure_connected()

    assert captured["broker_type"] == "tws"
    assert captured["kwargs"]["tws_submit_enabled"] is False


@pytest.mark.asyncio
async def test_tws_submit_disabled_when_paper_mode_not_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.broker_service.get_settings",
        lambda: _patched_settings(broker_provider="tws", tws_enabled=True),
    )
    monkeypatch.setattr(
        "app.services.broker_service.get_broker_mode_metadata",
        lambda: {
            "broker": "ibkr",
            "mode": "paper",
            "paper_trading_enabled": False,
            "live_execution_enabled": False,
        },
    )
    captured: dict = {}

    def fake_create(broker_type, **kwargs):
        captured["broker_type"] = broker_type
        captured["kwargs"] = kwargs
        return MagicMock(spec=TwsBroker)

    monkeypatch.setattr(
        "app.services.broker_service.BrokerGatewayFactory.create",
        staticmethod(fake_create),
    )

    svc = BrokerService()
    await svc.ensure_connected()

    assert captured["kwargs"]["tws_submit_enabled"] is False
