from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.feature_adapter_service import FeatureAdapterRequest, FeatureAdapterService
from app.services.feature_service import FeatureSnapshotPayload


def _bar(ts: datetime, close: Decimal) -> SimpleNamespace:
    return SimpleNamespace(
        ts=ts,
        open=close - Decimal("0.1"),
        high=close + Decimal("0.2"),
        low=close - Decimal("0.3"),
        close=close,
        volume=Decimal("1000"),
    )


def _quote(ts: datetime, bid: Decimal | None, ask: Decimal | None) -> SimpleNamespace:
    return SimpleNamespace(ts=ts, bid=bid, ask=ask)


def test_build_snapshot_maps_and_calls_feature_engine(monkeypatch) -> None:
    asset_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    bars = [
        _bar(now + timedelta(minutes=2), Decimal("101.0")),
        _bar(now + timedelta(minutes=1), Decimal("100.5")),
        _bar(now + timedelta(minutes=3), Decimal("101.5")),
    ]
    quotes = [
        _quote(now + timedelta(minutes=1), Decimal("100.0"), Decimal("100.1")),
        _quote(now + timedelta(minutes=2), None, Decimal("100.2")),
        _quote(now + timedelta(minutes=3), Decimal("100.2"), Decimal("100.3")),
    ]

    first_exec = MagicMock()
    first_exec.scalars.return_value.all.return_value = bars

    second_exec = MagicMock()
    second_exec.scalars.return_value.all.return_value = quotes

    session = MagicMock()
    session.execute.side_effect = [first_exec, second_exec]

    captured = {}

    def fake_build_snapshot(payload):
        captured["payload"] = payload
        return FeatureSnapshotPayload(
            ema_fast=1.0,
            ema_slow=2.0,
            rsi=50.0,
            atr=1.2,
            adx=20.0,
            volatility_score=50.0,
            liquidity_score=60.0,
            trend_score=0.2,
            momentum_score=0.1,
            regime_preclassification="range",
            market_quality_flag=True,
        )

    monkeypatch.setattr("app.services.feature_adapter_service.build_feature_snapshot", fake_build_snapshot)

    service = FeatureAdapterService(session)
    result = service.build_snapshot(
        FeatureAdapterRequest(asset_id=asset_id, timeframe="1m", bar_limit=3, quote_limit=3)
    )

    assert result.market_quality_flag is True

    first_stmt = session.execute.call_args_list[0].args[0]
    second_stmt = session.execute.call_args_list[1].args[0]

    first_order_sql = str(next(iter(first_stmt._order_by_clauses))).lower()
    second_order_sql = str(next(iter(second_stmt._order_by_clauses))).lower()
    assert "bars.ts" in first_order_sql
    assert "desc" in first_order_sql
    assert "quotes.ts" in second_order_sql
    assert "desc" in second_order_sql
    assert first_stmt._limit_clause.value == 3
    assert second_stmt._limit_clause.value == 3

    payload = captured["payload"]
    assert len(payload.bars) == 3
    assert payload.bars[0].close == 100.5
    assert payload.bars[-1].close == 101.5

    assert payload.quotes is not None
    assert len(payload.quotes) == 2
    assert payload.quotes[0].bid == 100.0
    assert payload.quotes[1].ask == 100.3


def test_build_snapshot_handles_missing_quotes_safely(monkeypatch) -> None:
    asset_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    bars = [_bar(now + timedelta(minutes=i), Decimal("100.0") + Decimal(i)) for i in range(40)]
    quotes = [
        _quote(now + timedelta(minutes=1), None, Decimal("100.1")),
        _quote(now + timedelta(minutes=2), Decimal("100.2"), None),
    ]

    first_exec = MagicMock()
    first_exec.scalars.return_value.all.return_value = bars

    second_exec = MagicMock()
    second_exec.scalars.return_value.all.return_value = quotes

    session = MagicMock()
    session.execute.side_effect = [first_exec, second_exec]

    captured = {}

    def fake_build_snapshot(payload):
        captured["payload"] = payload
        return FeatureSnapshotPayload(
            ema_fast=1.0,
            ema_slow=2.0,
            rsi=50.0,
            atr=1.2,
            adx=20.0,
            volatility_score=50.0,
            liquidity_score=0.0,
            trend_score=0.2,
            momentum_score=0.1,
            regime_preclassification="range",
            market_quality_flag=False,
        )

    monkeypatch.setattr("app.services.feature_adapter_service.build_feature_snapshot", fake_build_snapshot)

    service = FeatureAdapterService(session)
    service.build_snapshot(FeatureAdapterRequest(asset_id=asset_id, timeframe="5m", bar_limit=40, quote_limit=2))

    first_stmt = session.execute.call_args_list[0].args[0]
    second_stmt = session.execute.call_args_list[1].args[0]
    assert first_stmt._limit_clause.value == 40
    assert second_stmt._limit_clause.value == 2

    payload = captured["payload"]
    assert payload.quotes is None
