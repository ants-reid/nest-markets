from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.cockpit_trade_close_explanations_service import (
    get_cockpit_trade_close_explanations,
)


class _DummySession:
    pass


def _asset(symbol: str):
    return SimpleNamespace(id=uuid4(), symbol=symbol)


def _position(
    *,
    asset_id,
    signal_id=None,
    status: str = "closed",
    side: str = "long",
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
    created_at: datetime | None = None,
    close_reason: str | None = None,
    close_price: float | None = None,
    target_price: float | None = None,
    stop_price: float | None = None,
    realized_pnl: float | None = None,
):
    return SimpleNamespace(
        id=uuid4(),
        asset_id=asset_id,
        signal_id=signal_id,
        status=status,
        side=side,
        opened_at=opened_at,
        closed_at=closed_at,
        created_at=created_at or opened_at,
        close_reason=close_reason,
        close_price=close_price,
        target_price=target_price,
        stop_price=stop_price,
        realized_pnl=realized_pnl,
    )


def _paper_order(*, signal_id, status: str = "closed"):
    return SimpleNamespace(id=uuid4(), signal_id=signal_id, status=status, created_at=datetime.now(timezone.utc))


def _signal_outcome(*, signal_id, predicted_direction_correct: bool | None = None, actual_pnl_pct: float | None = None):
    return SimpleNamespace(
        id=uuid4(),
        signal_id=signal_id,
        predicted_direction_correct=predicted_direction_correct,
        actual_pnl_pct=actual_pnl_pct,
        closed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


def _risk_decision(*, signal_id, approved: str = "approved", blocking_rule: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        signal_id=signal_id,
        approved=approved,
        blocking_rule=blocking_rule,
        block_reason_code=None,
        created_at=datetime.now(timezone.utc),
    )


def test_empty_response_returns_safe_summary_and_limitations(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_assets", lambda session: ({}, {}))
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_closed_positions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_signal_outcomes", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_risk_decisions", lambda session: [])

    report = get_cockpit_trade_close_explanations(_DummySession(), now_utc=now)

    assert report.mode == "paper"
    assert report.summary.total_closed_trades == 0
    assert report.explanations == []
    assert report.limitations


def test_closed_paper_trades_are_surfaced_read_only(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    asset = _asset("AAPL")
    signal_id = uuid4()
    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_assets",
        lambda session: ({str(asset.id): "AAPL"}, {str(asset.id): None}),
    )
    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_closed_positions",
        lambda session: [
            _position(
                asset_id=asset.id,
                signal_id=signal_id,
                opened_at=now - timedelta(hours=3),
                closed_at=now - timedelta(hours=1),
                close_reason="target hit",
                close_price=110.0,
                target_price=110.0,
                realized_pnl=10.0,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_paper_orders",
        lambda session: [_paper_order(signal_id=signal_id, status="closed")],
    )
    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_signal_outcomes",
        lambda session: [_signal_outcome(signal_id=signal_id, predicted_direction_correct=True, actual_pnl_pct=1.2)],
    )
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_risk_decisions", lambda session: [])

    report = get_cockpit_trade_close_explanations(_DummySession(), now_utc=now)

    assert report.summary.total_closed_trades == 1
    assert len(report.explanations) == 1
    item = report.explanations[0]
    assert item.close_label == "target_hit"
    assert item.paper_order_id is not None
    assert item.is_actionable is False
    assert item.asset_id == str(asset.id)
    assert item.asset_detail_path == f"/asset-cards/{asset.id}"
    assert item.has_asset_context is True


def test_unknown_close_reason_returns_unknown_not_fabricated(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    asset = _asset("MSFT")
    signal_id = uuid4()

    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_assets",
        lambda session: ({str(asset.id): "MSFT"}, {str(asset.id): None}),
    )
    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_closed_positions",
        lambda session: [
            _position(
                asset_id=asset.id,
                signal_id=signal_id,
                opened_at=now - timedelta(hours=4),
                closed_at=now - timedelta(hours=2),
                close_reason=None,
                close_price=None,
                target_price=210.0,
                stop_price=190.0,
                realized_pnl=None,
            )
        ],
    )
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_signal_outcomes", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_risk_decisions", lambda session: [])

    report = get_cockpit_trade_close_explanations(_DummySession(), now_utc=now)

    assert len(report.explanations) == 1
    item = report.explanations[0]
    assert item.close_label == "unknown"
    assert item.close_reason is None
    assert "close_reason" in item.missing_data


def test_close_reason_inference_requires_evidence(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    asset = _asset("NVDA")
    signal_id = uuid4()

    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_assets",
        lambda session: ({str(asset.id): "NVDA"}, {str(asset.id): None}),
    )
    monkeypatch.setattr(
        "app.services.cockpit_trade_close_explanations_service._load_closed_positions",
        lambda session: [
            _position(
                asset_id=asset.id,
                signal_id=signal_id,
                opened_at=now - timedelta(hours=5),
                closed_at=now - timedelta(hours=1),
                close_reason=None,
                close_price=300.0,
                target_price=300.0,
                stop_price=280.0,
                realized_pnl=8.0,
            )
        ],
    )
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_paper_orders", lambda session: [_paper_order(signal_id=signal_id)])
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_signal_outcomes", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_trade_close_explanations_service._load_risk_decisions", lambda session: [_risk_decision(signal_id=signal_id)])

    report = get_cockpit_trade_close_explanations(_DummySession(), now_utc=now)

    assert len(report.explanations) == 1
    assert report.explanations[0].close_label == "target_hit"
    assert all(item.is_actionable is False for item in report.explanations)
