from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.cockpit_daily_scoreboard_service import get_cockpit_daily_scoreboard


class _DummySession:
    pass


def _asset(symbol: str):
    return SimpleNamespace(id=uuid4(), symbol=symbol)


def _paper_order(*, submitted_at: datetime | None = None, created_at: datetime | None = None):
    ts = submitted_at or created_at
    return SimpleNamespace(
        id=uuid4(),
        submitted_at=submitted_at,
        created_at=created_at,
        timestamp=ts,
    )


def _position(
    *,
    asset_id,
    side: str = "long",
    status: str = "open",
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
    realized_pnl: float | None = None,
    unrealized_pnl: float | None = None,
):
    return SimpleNamespace(
        id=uuid4(),
        asset_id=asset_id,
        side=side,
        status=status,
        opened_at=opened_at,
        closed_at=closed_at,
        created_at=opened_at,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        opened_by="auto_paper",
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


def _risk_decision(*, approved: str = "approved", signal_id=None, blocking_rule: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        approved=approved,
        signal_id=signal_id,
        blocking_rule=blocking_rule,
        block_reason_code=None,
        created_at=datetime.now(timezone.utc),
    )


def test_empty_response_returns_safe_summary_and_limitations(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_assets", lambda session: ({}, {}))
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_positions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_risk_decisions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_incidents", lambda session: [])

    report = get_cockpit_daily_scoreboard(_DummySession(), now_utc=now)

    assert report.mode == "paper"
    assert report.summary.trades_opened_today == 0
    assert report.summary.trades_closed_today == 0
    assert report.summary.open_positions_now == 0
    assert report.performance.realized_pnl_today == 0
    assert report.performance.unrealized_pnl_snapshot == 0
    assert report.top_contributors.items == []
    assert report.limitations


def test_opened_and_closed_counts_and_pnl_when_supported(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    earlier = now - timedelta(hours=2)
    asset_a = _asset("AAPL")
    asset_b = _asset("MSFT")

    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_assets",
        lambda session: (
            {str(asset_a.id): "AAPL", str(asset_b.id): "MSFT"},
            {str(asset_a.id): None, str(asset_b.id): None},
        ),
    )
    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_paper_orders",
        lambda session: [
            _paper_order(submitted_at=earlier),
            _paper_order(submitted_at=now - timedelta(days=1)),
        ],
    )
    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_positions",
        lambda session: [
            _position(asset_id=asset_a.id, side="long", status="open", opened_at=earlier, unrealized_pnl=3.5),
            _position(asset_id=asset_a.id, side="long", status="closed", opened_at=earlier, closed_at=now - timedelta(minutes=30), realized_pnl=10.0),
            _position(asset_id=asset_b.id, side="short", status="closed", opened_at=earlier, closed_at=now - timedelta(minutes=15), realized_pnl=-2.0),
        ],
    )
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_risk_decisions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_incidents", lambda session: [])

    report = get_cockpit_daily_scoreboard(_DummySession(), now_utc=now)

    assert report.summary.trades_opened_today == 1
    assert report.summary.trades_closed_today == 2
    assert report.summary.open_positions_now == 1
    assert report.performance.realized_pnl_today == 8.0
    assert report.performance.unrealized_pnl_snapshot == 3.5
    assert report.performance.net_pnl_today == 11.5
    assert report.performance.win_count == 1
    assert report.performance.loss_count == 1
    assert report.performance.flat_count == 0
    assert report.open_positions.long_count == 1
    assert report.open_positions.short_count == 0


def test_top_contributors_only_render_with_evidence(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    earlier = now - timedelta(hours=3)
    asset_a = _asset("AAPL")

    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_assets",
        lambda session: ({str(asset_a.id): "AAPL"}, {str(asset_a.id): None}),
    )
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_paper_orders", lambda session: [])
    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_positions",
        lambda session: [
            _position(asset_id=asset_a.id, status="closed", opened_at=earlier, closed_at=now - timedelta(minutes=20), realized_pnl=None),
        ],
    )
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_risk_decisions", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_incidents", lambda session: [])

    report = get_cockpit_daily_scoreboard(_DummySession(), now_utc=now)

    assert report.top_contributors.count == 1
    assert report.top_contributors.items[0].symbol == "AAPL"
    assert report.top_contributors.items[0].realized_pnl is None
    assert report.top_contributors.items[0].contribution_label == "unknown"
    assert report.top_contributors.items[0].asset_id == str(asset_a.id)
    assert report.top_contributors.items[0].asset_detail_path == f"/asset-cards/{asset_a.id}"
    assert report.top_contributors.items[0].has_asset_context is True


def test_missing_optional_metrics_do_not_crash(monkeypatch):
    now = datetime(2026, 5, 22, 21, 0, tzinfo=timezone.utc)
    earlier = now - timedelta(hours=2)
    asset = _asset("NVDA")

    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_assets",
        lambda session: ({str(asset.id): "NVDA"}, {str(asset.id): None}),
    )
    monkeypatch.setattr("app.services.cockpit_daily_scoreboard_service._load_paper_orders", lambda session: [_paper_order(submitted_at=earlier)])
    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_positions",
        lambda session: [
            _position(asset_id=asset.id, status="open", opened_at=earlier, unrealized_pnl=None),
            _position(asset_id=asset.id, status="closed", opened_at=earlier, closed_at=now - timedelta(minutes=10), realized_pnl=None),
        ],
    )
    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_risk_decisions",
        lambda session: [_risk_decision(approved="rejected", signal_id=uuid4(), blocking_rule="spread_too_wide")],
    )
    monkeypatch.setattr(
        "app.services.cockpit_daily_scoreboard_service._load_incidents",
        lambda session: [
            _incident(
                severity="critical",
                source="monitor",
                code="monitor.feed_down",
                title="Feed degraded",
                created_at=now - timedelta(minutes=5),
            )
        ],
    )

    report = get_cockpit_daily_scoreboard(_DummySession(), now_utc=now)

    assert report.performance.realized_pnl_today is None
    assert report.performance.unrealized_pnl_snapshot is None
    assert report.performance.win_count is None
    assert report.summary.day_status in {"monitor_attention", "review_required", "data_incomplete"}
    assert report.risk_and_monitor_notes
    assert report.review_priorities
    assert report.limitations
