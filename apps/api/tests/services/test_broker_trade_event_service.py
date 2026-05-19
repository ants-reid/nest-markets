"""MH-47 tests for broker trade/fill event normalization service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from app.services.broker_trade_event_service import (
    BrokerTradeEventService,
    normalize_trade_event,
    sum_today_realized_pnl_from_raw_events,
)


def test_normalize_trade_event_maps_common_ibkr_fields():
    raw = {
        "orderId": "1001",
        "order_ref": "P-123",
        "symbol": "aapl",
        "side": "buy",
        "size": "10",
        "price": "185.25",
        "commission": "1.20",
        "net_amount": "-1853.70",
        "realizedPnl": "12.5",
        "trade_time": "2026-04-28T12:00:00+00:00",
    }

    out = normalize_trade_event(raw)

    assert out.external_trade_id == "1001"
    assert out.broker_order_id == "P-123"
    assert out.symbol == "AAPL"
    assert out.side == "BUY"
    assert out.quantity == pytest.approx(10.0)
    assert out.fill_price == pytest.approx(185.25)
    assert out.realized_pnl == pytest.approx(12.5)
    assert out.trade_ts is not None
    assert len(out.event_fingerprint) == 64


def test_sum_today_realized_pnl_from_raw_events_filters_by_today():
    today = date.today().isoformat()
    yesterday = "2020-01-01"
    events = [
        {"trade_time": f"{today}T10:00:00+00:00", "realizedPnl": "5"},
        {"trade_time": f"{today}T11:00:00+00:00", "realized_pnl": 7.5},
        {"trade_time": f"{yesterday}T11:00:00+00:00", "realized": 99},
    ]

    total = sum_today_realized_pnl_from_raw_events(events)
    assert total == pytest.approx(12.5)


def test_ingest_trade_events_deduplicates_on_fingerprint():
    session = MagicMock()
    service = BrokerTradeEventService(session)

    # first event not found, second considered duplicate
    session.query.return_value.filter.return_value.first.side_effect = [None, object()]

    raw = {
        "orderId": "1001",
        "order_ref": "P-123",
        "symbol": "AAPL",
        "side": "BUY",
        "size": "10",
        "price": "185.25",
        "trade_time": datetime.now(UTC).isoformat(),
    }

    result = service.ingest_trade_events(
        [raw, raw],
        broker_provider="ibkr",
        account_id="DU123456",
        source="broker_account_trades",
    )

    assert result["received"] == 2
    assert result["inserted"] == 1
    assert result["skipped"] == 1
    assert session.add.call_count == 1
