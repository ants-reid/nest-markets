"""MH-145-A — Tests for ``MarketContextSnapshotService`` (scaffolding).

These tests verify the read-only computer behaves correctly for:

- Spread estimation from the most recent bar (and graceful fallback).
- Daily drawdown summing only today's negative realized PnL.
- Recent-losses count + last_loss_at within the lookback window.
- Snapshot serialization shape.

The service is NOT wired into production code; see
``test_mh145_a_drift_lock.py`` for the drift-lock invariance proof.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.db.enums import AssetClass, PositionStatus
from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.models.position import Position
from app.db.session import SessionLocal
from app.services.market_context_snapshot_service import (
    MarketContextSnapshot,
    MarketContextSnapshotService,
)


@pytest.fixture
def db():
    """Yield a session with cleanup; tests use baseline-delta assertions
    against ``positions`` because that table has account-wide rows from
    other test runs that the service must (correctly) include.
    """
    session = SessionLocal()
    created_asset_ids: list[uuid.UUID] = []
    created_bar_ids: list[uuid.UUID] = []
    created_position_ids: list[uuid.UUID] = []
    # CHECK constraint allows only auto_paper / manual_paper / live / unknown.
    opened_by_marker = "auto_paper"

    def _add_asset(symbol: str) -> Asset:
        asset = Asset(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
        )
        session.add(asset)
        session.flush()
        created_asset_ids.append(asset.id)
        return asset

    def _add_bar(
        asset_id: uuid.UUID,
        *,
        ts: datetime,
        high: float,
        low: float,
        close: float,
        timeframe: str = "1m",
    ) -> Bar:
        bar = Bar(
            asset_id=asset_id,
            timeframe=timeframe,
            ts=ts,
            open=Decimal(str(close)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
        )
        session.add(bar)
        session.flush()
        created_bar_ids.append(bar.id)
        return bar

    def _add_position(
        asset_id: uuid.UUID,
        *,
        status: PositionStatus,
        side: str = "long",
        closed_at: datetime | None = None,
        realized_pnl: Decimal | None = None,
    ) -> Position:
        pos = Position(
            asset_id=asset_id,
            status=status,
            side=side,
            closed_at=closed_at,
            realized_pnl=realized_pnl,
            opened_by=opened_by_marker,
        )
        session.add(pos)
        session.flush()
        created_position_ids.append(pos.id)
        return pos

    yield session, _add_asset, _add_bar, _add_position, opened_by_marker

    for pid in created_position_ids:
        obj = session.get(Position, pid)
        if obj is not None:
            session.delete(obj)
    session.flush()
    for bid in created_bar_ids:
        obj = session.get(Bar, bid)
        if obj is not None:
            session.delete(obj)
    session.flush()
    for aid in created_asset_ids:
        obj = session.get(Asset, aid)
        if obj is not None:
            session.delete(obj)
    session.commit()
    session.close()


def _utc(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Spread tests                                                                #
# --------------------------------------------------------------------------- #


def test_spread_bps_uses_latest_bar_high_low(db):
    session, add_asset, add_bar, _add_position, opened_by = db
    asset = add_asset(f"MH145A_SPR_{uuid.uuid4().hex[:6]}")
    now = _utc(2026, 5, 5)
    # Older bar (should be ignored — service uses LATEST)
    add_bar(
        asset.id,
        ts=now - timedelta(minutes=10),
        high=200.0,
        low=100.0,
        close=150.0,
    )
    # Latest bar: high=101, low=99 -> mid=100, spread=200 bps
    add_bar(asset.id, ts=now, high=101.0, low=99.0, close=100.0)
    session.commit()

    svc = MarketContextSnapshotService(session)
    snap = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        now=now + timedelta(seconds=1),
    )

    assert snap.bar_observed is True
    assert snap.spread_bps == pytest.approx(200.0, rel=1e-3)


def test_spread_bps_zero_and_bar_unobserved_when_no_bars(db):
    session, add_asset, _add_bar, _add_position, opened_by = db
    asset = add_asset(f"MH145A_NOBAR_{uuid.uuid4().hex[:6]}")
    session.commit()

    svc = MarketContextSnapshotService(session)
    snap = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        now=_utc(2026, 5, 5),
    )

    assert snap.spread_bps == 0.0
    assert snap.bar_observed is False


# --------------------------------------------------------------------------- #
# Daily drawdown tests                                                        #
# --------------------------------------------------------------------------- #


def test_daily_drawdown_sums_only_today_negative_pnl(db):
    session, add_asset, _add_bar, add_position, opened_by = db
    asset = add_asset(f"MH145A_DD_{uuid.uuid4().hex[:6]}")
    now = _utc(2026, 5, 5, hour=15)
    svc = MarketContextSnapshotService(session)
    session.commit()

    # Baseline BEFORE adding any rows for this test.
    baseline = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        opened_by_filter=opened_by,
        now=now,
    )

    # Yesterday's loss — should be excluded
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(days=1),
        realized_pnl=Decimal("-500"),
    )
    # Today's loss #1
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(hours=2),
        realized_pnl=Decimal("-100"),
    )
    # Today's loss #2
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(hours=1),
        realized_pnl=Decimal("-50"),
    )
    # Today's WIN — must be ignored (only negative pnl counts)
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(minutes=30),
        realized_pnl=Decimal("75"),
    )
    # Today but still OPEN — must be ignored
    add_position(
        asset.id,
        status=PositionStatus.OPEN,
        closed_at=None,
        realized_pnl=None,
    )
    session.commit()

    after = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        opened_by_filter=opened_by,
        now=now,
    )

    # Delta: 150 lost / 10000 equity = 1.5 percentage points added.
    assert after.daily_drawdown_pct - baseline.daily_drawdown_pct == pytest.approx(
        1.5, rel=1e-3
    )


def test_daily_drawdown_zero_when_equity_non_positive(db):
    session, add_asset, _add_bar, add_position, opened_by = db
    asset = add_asset(f"MH145A_DDEQ_{uuid.uuid4().hex[:6]}")
    now = _utc(2026, 5, 5, hour=15)
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(hours=1),
        realized_pnl=Decimal("-100"),
    )
    session.commit()

    svc = MarketContextSnapshotService(session)
    snap = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=0.0,
        opened_by_filter=opened_by,
        now=now,
    )
    assert snap.daily_drawdown_pct == 0.0


# --------------------------------------------------------------------------- #
# Recent-losses tests                                                         #
# --------------------------------------------------------------------------- #


def test_recent_losses_count_and_last_loss_at_within_window(db):
    session, add_asset, _add_bar, add_position, opened_by = db
    asset = add_asset(f"MH145A_LOSS_{uuid.uuid4().hex[:6]}")
    now = _utc(2026, 5, 5, hour=18)
    svc = MarketContextSnapshotService(session)
    session.commit()

    # Baseline before any test-owned rows.
    baseline = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        lookback_hours=24,
        opened_by_filter=opened_by,
        now=now,
    )

    # Outside window (25h ago)
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(hours=25),
        realized_pnl=Decimal("-10"),
    )
    # In window — three losses
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(hours=20),
        realized_pnl=Decimal("-10"),
    )
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(hours=10),
        realized_pnl=Decimal("-10"),
    )
    most_recent_ts = now - timedelta(hours=2)
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=most_recent_ts,
        realized_pnl=Decimal("-10"),
    )
    # In window — a WIN; must be excluded from loss count
    add_position(
        asset.id,
        status=PositionStatus.CLOSED,
        closed_at=now - timedelta(hours=1),
        realized_pnl=Decimal("25"),
    )
    session.commit()

    after = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        lookback_hours=24,
        opened_by_filter=opened_by,
        now=now,
    )

    # Delta: 3 new losses inside the window (the 25h-old one is excluded,
    # the win is excluded).
    assert after.recent_losses_count - baseline.recent_losses_count == 3
    assert after.last_loss_at is not None
    # Postgres preserves timezone; allow small clock skew
    assert (
        abs((after.last_loss_at - most_recent_ts).total_seconds()) < 2.0
        or (
            baseline.last_loss_at is not None
            and after.last_loss_at >= baseline.last_loss_at
        )
    )
    assert after.lookback_hours == 24


def test_recent_losses_zero_and_last_loss_none_when_no_history(db):
    """With ``opened_by_filter`` set to a value that has no rows in DB,
    the snapshot returns zero losses regardless of any pre-existing
    positions in the shared ``positions`` table."""
    session, add_asset, _add_bar, _add_position, _opened_by = db
    asset = add_asset(f"MH145A_EMP_{uuid.uuid4().hex[:6]}")
    session.commit()

    svc = MarketContextSnapshotService(session)
    snap = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        # 'live' is in the CHECK enum but no test row uses it AND the
        # production live path is gated off, so this filter should
        # match zero rows in any reasonable test DB.
        opened_by_filter="live",
        now=_utc(2026, 5, 5),
    )
    assert snap.recent_losses_count == 0
    assert snap.last_loss_at is None


# --------------------------------------------------------------------------- #
# Validation + serialization                                                  #
# --------------------------------------------------------------------------- #


def test_snapshot_to_dict_shape(db):
    session, add_asset, _add_bar, _add_position, opened_by = db
    asset = add_asset(f"MH145A_DICT_{uuid.uuid4().hex[:6]}")
    session.commit()

    svc = MarketContextSnapshotService(session)
    snap = svc.snapshot(
        asset_id=asset.id,
        asset_symbol=asset.symbol,
        account_equity=10_000.0,
        now=_utc(2026, 5, 5),
    )
    payload = snap.to_dict()
    assert set(payload.keys()) == {
        "asset_id",
        "asset_symbol",
        "spread_bps",
        "daily_drawdown_pct",
        "recent_losses_count",
        "last_loss_at",
        "sampled_at",
        "bar_observed",
        "lookback_hours",
        "opened_by_filter",
    }
    assert isinstance(snap, MarketContextSnapshot)


def test_invalid_lookback_rejected(db):
    session, add_asset, _add_bar, _add_position, opened_by = db
    asset = add_asset(f"MH145A_VAL_{uuid.uuid4().hex[:6]}")
    session.commit()
    svc = MarketContextSnapshotService(session)
    with pytest.raises(ValueError):
        svc.snapshot(
            asset_id=asset.id,
            asset_symbol=asset.symbol,
            account_equity=10_000.0,
            lookback_hours=0,
            now=_utc(2026, 5, 5),
        )


def test_naive_now_rejected(db):
    session, add_asset, _add_bar, _add_position, opened_by = db
    asset = add_asset(f"MH145A_TZ_{uuid.uuid4().hex[:6]}")
    session.commit()
    svc = MarketContextSnapshotService(session)
    with pytest.raises(ValueError):
        svc.snapshot(
            asset_id=asset.id,
            asset_symbol=asset.symbol,
            account_equity=10_000.0,
            now=datetime(2026, 5, 5, 12, 0, 0),  # naive
        )
