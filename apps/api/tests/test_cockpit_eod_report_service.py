from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.cockpit_eod_report_service import get_cockpit_eod_report


class _DummySession:
    pass


def _asset(symbol: str):
    return SimpleNamespace(id=uuid4(), symbol=symbol)


def _paper_order(timestamp: datetime):
    return SimpleNamespace(submitted_at=timestamp, created_at=timestamp, timestamp=timestamp)


def _position(
    *,
    asset_id,
    side: str = "long",
    qty: float | None = 1.0,
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
    realized_pnl: float | None = None,
    unrealized_pnl: float | None = None,
    close_reason: str | None = None,
    opened_by: str = "auto_paper",
):
    return SimpleNamespace(
        id=uuid4(),
        asset_id=asset_id,
        side=side,
        qty=qty,
        opened_at=opened_at,
        closed_at=closed_at,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        close_reason=close_reason,
        opened_by=opened_by,
    )


def _outcome(*, closed_at: datetime, predicted_direction_correct: bool | None, actual_pnl_pct: float | None):
    return SimpleNamespace(
        id=uuid4(),
        closed_at=closed_at,
        predicted_direction_correct=predicted_direction_correct,
        actual_pnl_pct=actual_pnl_pct,
    )


def _incident(*, severity: str, code: str, title: str, source: str, created_at: datetime, detail: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        severity=severity,
        code=code,
        title=title,
        source=source,
        created_at=created_at,
        detail=detail,
    )


def test_empty_report_returns_safe_defaults(monkeypatch):
    now = datetime(2026, 5, 22, 20, 15, tzinfo=timezone.utc)
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_assets", lambda session: {})
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_positions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_signal_outcomes", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_incidents", lambda session: [])

    report = get_cockpit_eod_report(_DummySession(), now_utc=now)

    assert report.mode == "paper"
    assert report.report_date == "2026-05-22"
    assert report.summary.opened_today == 0
    assert report.summary.closed_today == 0
    assert report.summary.open_positions_now == 0
    assert report.paper_activity.current_open_positions == 0
    assert report.pnl.realized_day == 0
    assert report.pnl.unrealized_snapshot == 0
    assert report.alerts_or_incidents == []
    assert report.lessons == []
    assert report.recommended_actions
    assert report.limitations


def test_report_counts_today_activity_and_pnl(monkeypatch):
    now = datetime(2026, 5, 22, 20, 15, tzinfo=timezone.utc)
    earlier = now - timedelta(hours=2)
    yesterday = now - timedelta(days=1)
    asset_a = _asset("AAPL")
    asset_b = _asset("MSFT")

    monkeypatch.setattr(
        "app.services.cockpit_eod_report_service._load_assets",
        lambda session: {str(asset_a.id): asset_a.symbol, str(asset_b.id): asset_b.symbol},
    )
    monkeypatch.setattr(
        "app.services.cockpit_eod_report_service._load_paper_orders",
        lambda session: [_paper_order(earlier), _paper_order(yesterday)],
    )
    monkeypatch.setattr(
        "app.services.cockpit_eod_report_service._load_positions",
        lambda session: [
            _position(asset_id=asset_a.id, opened_at=earlier, unrealized_pnl=5.5),
            _position(asset_id=asset_a.id, opened_at=earlier, closed_at=now - timedelta(hours=1), realized_pnl=12.0, close_reason="target_hit"),
            _position(asset_id=asset_b.id, opened_at=earlier, closed_at=now - timedelta(minutes=30), realized_pnl=-4.0, close_reason="stop_hit"),
        ],
    )
    monkeypatch.setattr(
        "app.services.cockpit_eod_report_service._load_signal_outcomes",
        lambda session: [
            _outcome(closed_at=now - timedelta(hours=1), predicted_direction_correct=True, actual_pnl_pct=2.5),
            _outcome(closed_at=now - timedelta(minutes=45), predicted_direction_correct=False, actual_pnl_pct=-1.25),
        ],
    )
    monkeypatch.setattr(
        "app.services.cockpit_eod_report_service._load_incidents",
        lambda session: [
            _incident(severity="critical", code="monitor.feed_down", title="Feed degraded", source="monitor", created_at=now - timedelta(hours=1), detail="Primary feed stalled."),
            _incident(severity="info", code="ui.note", title="Benign note", source="ui", created_at=now - timedelta(hours=3), detail=None),
        ],
    )

    report = get_cockpit_eod_report(_DummySession(), now_utc=now)

    assert report.summary.opened_today == 1
    assert report.summary.closed_today == 2
    assert report.summary.open_positions_now == 1
    assert report.paper_activity.current_open_positions == 1
    assert report.pnl.realized_day == 8.0
    assert report.pnl.unrealized_snapshot == 5.5
    assert report.closed_positions.wins == 1
    assert report.closed_positions.losses == 1
    assert report.closed_positions.best_trade is not None
    assert report.closed_positions.best_trade.asset_symbol == "AAPL"
    assert report.closed_positions.worst_trade is not None
    assert report.closed_positions.worst_trade.asset_symbol == "MSFT"
    assert len(report.alerts_or_incidents) == 1
    assert report.alerts_or_incidents[0].title == "Feed degraded"
    assert len(report.monitor_notes) == 1
    assert report.lessons


def test_missing_optional_metrics_do_not_crash(monkeypatch):
    now = datetime(2026, 5, 22, 20, 15, tzinfo=timezone.utc)
    asset_a = _asset("AAPL")
    monkeypatch.setattr(
        "app.services.cockpit_eod_report_service._load_assets",
        lambda session: {str(asset_a.id): asset_a.symbol},
    )
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr(
        "app.services.cockpit_eod_report_service._load_positions",
        lambda session: [
            _position(asset_id=asset_a.id, opened_at=now - timedelta(hours=1), unrealized_pnl=None),
            _position(asset_id=asset_a.id, opened_at=now - timedelta(hours=2), closed_at=now - timedelta(minutes=10), realized_pnl=None),
        ],
    )
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_signal_outcomes", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_eod_report_service._load_incidents", lambda session: [])

    report = get_cockpit_eod_report(_DummySession(), now_utc=now)

    assert report.pnl.realized_day is None
    assert report.pnl.unrealized_snapshot is None
    assert report.closed_positions.wins is None
    assert report.closed_positions.unknown == 1
    assert any("Realized paper P&L is incomplete" in item for item in report.limitations)
    assert any("Unrealized paper P&L snapshot is incomplete" in item for item in report.limitations)