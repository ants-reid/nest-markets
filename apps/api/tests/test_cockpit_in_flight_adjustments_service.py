from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.cockpit_in_flight_adjustments_service import get_cockpit_in_flight_adjustments


class _DummySession:
    pass


def _asset(symbol: str):
    return SimpleNamespace(id=uuid4(), symbol=symbol)


def _position(
    *,
    asset_id,
    status: str = "open",
    side: str = "long",
    qty: float | None = 1.0,
    opened_at: datetime | None = None,
    created_at: datetime | None = None,
    avg_entry_price: float | None = 100.0,
    current_price: float | None = 101.0,
    stop_price: float | None = 95.0,
    target_price: float | None = 110.0,
    unrealized_pnl: float | None = 1.0,
    signal_id=None,
):
    return SimpleNamespace(
        id=uuid4(),
        asset_id=asset_id,
        status=status,
        side=side,
        qty=qty,
        opened_at=opened_at,
        created_at=created_at or opened_at,
        avg_entry_price=avg_entry_price,
        current_price=current_price,
        stop_price=stop_price,
        target_price=target_price,
        unrealized_pnl=unrealized_pnl,
        signal_id=signal_id,
    )


def _paper_order(
    *,
    asset_id,
    status: str = "accepted",
    created_at: datetime,
    submitted_at: datetime | None = None,
    side: str = "buy",
    qty: float | None = 1.0,
    quantity: float | None = None,
    order_type: str = "limit",
    signal_id=None,
):
    return SimpleNamespace(
        id=uuid4(),
        asset_id=asset_id,
        status=status,
        created_at=created_at,
        submitted_at=submitted_at,
        timestamp=created_at,
        side=side,
        qty=qty,
        quantity=quantity,
        order_type=order_type,
        signal_id=signal_id,
    )


def _recommendation(
    *,
    ticker: str,
    status: str = "draft",
    created_at: datetime,
    side: str = "BUY",
    quantity: float = 1.0,
    order_type: str = "LIMIT",
    confidence: float | None = 0.7,
    risk_score: float | None = 0.3,
    rationale: str | None = "test",
    signal_id=None,
):
    return SimpleNamespace(
        id=uuid4(),
        ticker=ticker,
        status=status,
        created_at=created_at,
        side=side,
        quantity=quantity,
        order_type=order_type,
        confidence=confidence,
        risk_score=risk_score,
        rationale=rationale,
        signal_id=signal_id,
    )


def _risk_decision(*, signal_id=None, approved: str = "approved", blocking_rule: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        signal_id=signal_id,
        approved=approved,
        blocking_rule=blocking_rule,
        block_reason_code=None,
        created_at=datetime.now(timezone.utc),
    )


def _incident(*, severity: str, source: str, code: str, title: str, created_at: datetime):
    return SimpleNamespace(
        id=uuid4(),
        severity=severity,
        source=source,
        code=code,
        title=title,
        detail=None,
        created_at=created_at,
    )


def test_empty_response_returns_safe_summary_and_limitations(monkeypatch):
    now = datetime(2026, 5, 22, 20, 15, tzinfo=timezone.utc)
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_assets", lambda session: {})
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_positions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_paper_recommendations", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_risk_decisions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_incidents", lambda session: [])

    report = get_cockpit_in_flight_adjustments(_DummySession(), now_utc=now)

    assert report.mode == "paper"
    assert report.summary.total_items == 0
    assert report.items == []
    assert report.limitations


def test_open_positions_and_orders_are_surfaced_read_only(monkeypatch):
    now = datetime(2026, 5, 22, 20, 15, tzinfo=timezone.utc)
    asset = _asset("AAPL")
    signal_id = uuid4()

    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_assets", lambda session: {str(asset.id): "AAPL"})
    monkeypatch.setattr(
        "app.services.cockpit_in_flight_adjustments_service._load_positions",
        lambda session: [
            _position(
                asset_id=asset.id,
                opened_at=now - timedelta(hours=2),
                created_at=now - timedelta(hours=2),
                signal_id=signal_id,
                unrealized_pnl=-3.5,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.cockpit_in_flight_adjustments_service._load_paper_orders",
        lambda session: [_paper_order(asset_id=asset.id, created_at=now - timedelta(minutes=5), signal_id=signal_id)],
    )
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_paper_recommendations", lambda session: [])
    monkeypatch.setattr(
        "app.services.cockpit_in_flight_adjustments_service._load_risk_decisions",
        lambda session: [_risk_decision(signal_id=signal_id, approved="rejected", blocking_rule="spread_too_wide")],
    )
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_incidents", lambda session: [])

    report = get_cockpit_in_flight_adjustments(_DummySession(), now_utc=now)

    assert report.summary.open_positions == 1
    assert report.summary.open_orders == 1
    assert len(report.items) == 2
    assert all(item.is_actionable is False for item in report.items)
    assert any(item.item_type == "paper_position" for item in report.items)
    assert any(item.item_type == "paper_order" for item in report.items)


def test_recommendations_are_surfaced_when_available(monkeypatch):
    now = datetime(2026, 5, 22, 20, 15, tzinfo=timezone.utc)

    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_assets", lambda session: {})
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_positions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr(
        "app.services.cockpit_in_flight_adjustments_service._load_paper_recommendations",
        lambda session: [
            _recommendation(
                ticker="MSFT",
                status="draft",
                created_at=now - timedelta(hours=7),
                confidence=0.48,
                risk_score=0.82,
                rationale="watch move",
            )
        ],
    )
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_risk_decisions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_incidents", lambda session: [])

    report = get_cockpit_in_flight_adjustments(_DummySession(), now_utc=now)

    assert report.summary.active_recommendations == 1
    assert len(report.items) == 1
    assert report.items[0].item_type == "paper_recommendation"
    assert report.items[0].adjustment_label in {"review_required", "risk_attention", "stale_data"}
    assert report.items[0].is_actionable is False


def test_missing_context_does_not_crash(monkeypatch):
    now = datetime(2026, 5, 22, 20, 15, tzinfo=timezone.utc)
    asset = _asset("NVDA")

    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_assets", lambda session: {str(asset.id): "NVDA"})
    monkeypatch.setattr(
        "app.services.cockpit_in_flight_adjustments_service._load_positions",
        lambda session: [
            _position(
                asset_id=asset.id,
                opened_at=now - timedelta(hours=1),
                current_price=None,
                stop_price=None,
                target_price=None,
                unrealized_pnl=None,
                signal_id=None,
            )
        ],
    )
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_paper_recommendations", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_in_flight_adjustments_service._load_risk_decisions", lambda session: [])
    monkeypatch.setattr(
        "app.services.cockpit_in_flight_adjustments_service._load_incidents",
        lambda session: [
            _incident(
                severity="critical",
                source="monitor",
                code="monitor.feed_down",
                title="Feed degraded",
                created_at=now - timedelta(minutes=20),
            )
        ],
    )

    report = get_cockpit_in_flight_adjustments(_DummySession(), now_utc=now)

    assert len(report.items) == 1
    assert report.items[0].missing_data
    assert report.monitor_notes
    assert all(item.is_actionable is False for item in report.items)
