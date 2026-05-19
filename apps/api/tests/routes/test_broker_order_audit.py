"""Route tests for broker paper order audit trail (MH-31)."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.clients.broker.broker_interface import OrderResult
from app.config import get_settings
from app.main import create_app
from app.services import audit_log_service


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _audit_log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(audit_log_service, "_AUDIT_LOG_PATH", tmp_path / "audit.jsonl")


def _payload(**overrides):
    data = {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "limit_price": 180.5,
    }
    data.update(overrides)
    return data


def test_dry_run_event_is_written_and_readable(client: TestClient):
    response = client.post("/broker/orders/dry-run", json=_payload())
    assert response.status_code == 200

    audit = client.get("/broker/orders/audit")
    assert audit.status_code == 200
    entries = audit.json()["entries"]
    assert len(entries) >= 1
    latest = entries[0]
    assert latest["event"] == "broker_order_event"
    assert latest["action"] == "dry_run"
    assert latest["ticker"] == "AAPL"
    assert latest["dry_run"] is True


def test_submit_blocked_event_is_audited(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    response = client.post("/broker/orders", json=_payload(order_type="MARKET", limit_price=None))
    assert response.status_code == 403

    audit = client.get("/broker/orders/audit")
    entries = audit.json()["entries"]
    assert len(entries) >= 1
    latest = entries[0]
    assert latest["action"] == "submit"
    assert latest["status"] == "BLOCKED"
    assert latest["dry_run"] is False


def test_submit_success_event_includes_broker_order_id(client: TestClient):
    fake_result = OrderResult(
        broker_order_id="PAPER-123",
        status="SUBMITTED",
        filled_price=Decimal("0"),
        filled_quantity=Decimal("0"),
        error_message=None,
    )

    fake_service = AsyncMock()
    fake_service.submit_order = AsyncMock(return_value=fake_result)

    with patch("app.api.routes.broker.get_broker_service", return_value=fake_service):
        response = client.post("/broker/orders", json=_payload(order_type="MARKET", limit_price=None))

    assert response.status_code == 200

    audit = client.get("/broker/orders/audit")
    entries = audit.json()["entries"]
    assert len(entries) >= 1
    latest = entries[0]
    assert latest["action"] == "submit"
    assert latest["status"] == "SUBMITTED"
    assert latest["broker_order_id"] == "PAPER-123"
    assert latest["dry_run"] is False
