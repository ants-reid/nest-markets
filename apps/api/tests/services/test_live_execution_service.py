from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.clients.broker.broker_interface import OrderResult
from app.services.live_execution_service import (
    LiveExecutionRequest,
    LiveExecutionService,
)


def test_live_execution_service_disabled_without_broker(monkeypatch) -> None:
    monkeypatch.delenv("LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("PAPER_TRADING_ENABLED", raising=False)
    service = LiveExecutionService(session=MagicMock(), broker=None)

    result = service.submit(
        LiveExecutionRequest(
            asset="AAPL",
            side="buy",
            qty=1,
            notional=100,
            stop_price=95,
            target_price=110,
        )
    )

    assert result.accepted is False
    assert result.status == "disabled"
    assert result.reason == "live_execution_disabled_in_mvp"


def test_live_execution_service_disabled_even_with_env_without_broker(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "1")
    service = LiveExecutionService(session=MagicMock(), broker=None)

    assert service.is_enabled() is False


def test_submit_order_still_blocks_and_audits() -> None:
    session = MagicMock()
    service = LiveExecutionService(session=session)

    try:
        service.submit_order(uuid4(), uuid4(), "long", 1.0)
    except Exception as exc:
        assert str(exc) == "live_execution_disabled in MVP"

    session.add.assert_called_once()


# ── BP-15.14: auto_live always blocked (Gate 4) ───────────────────────────────

def test_auto_live_mode_always_disabled(monkeypatch) -> None:
    """Gate 4: auto_live mode must never route to broker."""
    monkeypatch.setenv("PAPER_TRADING_ENABLED", "1")
    mock_broker = MagicMock()
    service = LiveExecutionService(session=MagicMock(), broker=mock_broker)

    result = service.submit(
        LiveExecutionRequest(
            asset="AAPL",
            side="buy",
            qty=100,
            notional=17500,
            stop_price=170,
            target_price=185,
            execution_mode="auto_live",
        )
    )

    assert result.accepted is False
    assert result.status == "disabled"
    assert result.reason == "live_execution_disabled_in_mvp"
    # Broker must NOT be called for live mode
    mock_broker.submit_order.assert_not_called()


def test_auto_paper_disabled_without_env(monkeypatch) -> None:
    """Paper mode returns disabled when PAPER_TRADING_ENABLED not set."""
    monkeypatch.delenv("PAPER_TRADING_ENABLED", raising=False)
    mock_broker = MagicMock()
    service = LiveExecutionService(session=MagicMock(), broker=mock_broker)

    result = service.submit(
        LiveExecutionRequest(
            asset="AAPL",
            side="buy",
            qty=100,
            notional=17500,
            stop_price=170,
            target_price=185,
            execution_mode="auto_paper",
        )
    )

    assert result.accepted is False
    assert result.status == "disabled"


def test_auto_paper_disabled_without_broker(monkeypatch) -> None:
    """Paper mode returns disabled when broker not wired."""
    monkeypatch.setenv("PAPER_TRADING_ENABLED", "1")
    service = LiveExecutionService(session=MagicMock(), broker=None)

    result = service.submit(
        LiveExecutionRequest(
            asset="AAPL",
            side="buy",
            qty=100,
            notional=17500,
            stop_price=170,
            target_price=185,
            execution_mode="auto_paper",
        )
    )

    assert result.accepted is False
    assert result.status == "disabled"


def test_auto_paper_blocked_by_default_via_broker_auto_submit_seam(monkeypatch) -> None:
    """Auto-paper must route through the broker auto-submit seam and stay blocked by default."""
    monkeypatch.setenv("PAPER_TRADING_ENABLED", "1")

    mock_broker = MagicMock()
    mock_broker.submit_order = AsyncMock(
        return_value=OrderResult(broker_order_id="P-12345", status="SUBMITTED")
    )

    service = LiveExecutionService(session=MagicMock(), broker=mock_broker)

    result = service.submit(
        LiveExecutionRequest(
            asset="AAPL",
            side="buy",
            qty=100,
            notional=17500,
            stop_price=170,
            target_price=185,
            execution_mode="auto_paper",
        )
    )

    assert result.accepted is False
    assert result.status == "disabled"
    assert "Auto trading is not enabled" in result.reason
    mock_broker.submit_order.assert_not_called()


def test_auto_paper_maps_future_shared_broker_submit_success(monkeypatch) -> None:
    """The auto-paper seam can map a future shared broker-service success without direct adapter submission here."""
    monkeypatch.setenv("PAPER_TRADING_ENABLED", "1")

    mock_broker = MagicMock()
    service = LiveExecutionService(session=MagicMock(), broker=mock_broker)

    with patch(
        "app.services.live_execution_service.BrokerService.submit_auto_order",
        return_value=OrderResult(broker_order_id="P-12345", status="SUBMITTED"),
    ) as mock_auto_submit:
        result = service.submit(
            LiveExecutionRequest(
                asset="AAPL",
                side="buy",
                qty=100,
                notional=17500,
                stop_price=170,
                target_price=185,
                execution_mode="auto_paper",
            )
        )

    assert result.accepted is True
    assert result.status == "paper_submitted"
    assert result.broker_order_id == "P-12345"
    mock_auto_submit.assert_called_once()
    mock_broker.submit_order.assert_not_called()

