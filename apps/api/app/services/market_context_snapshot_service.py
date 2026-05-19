"""MH-145-A — MarketContextSnapshotService (scaffolding, NOT wired).

Computes the three real values that the auto-paper worker currently
hardcodes to zero when constructing a ``RiskInput``:

- ``spread_bps`` — estimated from the latest bar high/low for the asset.
- ``daily_drawdown_pct`` — sum of negative ``realized_pnl`` for positions
  closed today (UTC), expressed as a percentage of account equity.
- ``recent_losses_count`` and ``last_loss_at`` — count + most recent
  timestamp of closed losing positions in a configurable lookback window
  (default 24h).

This module is **purely additive**. It is NOT imported by
``auto_paper_trader_worker.py`` and does NOT alter any trading control,
risk evaluator, or broker submission. Wiring is deferred to MH-145-B.

Drift lock:
- No mutations: all DB access is SELECT-only.
- Returns a frozen dataclass; callers cannot mutate.
- Defensive on missing data: returns 0.0 / 0 / None rather than raising,
  so a future writer cannot accidentally crash the worker.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.db.enums import PositionStatus
from app.db.models.bar import Bar
from app.db.models.position import Position


@dataclass(frozen=True)
class MarketContextSnapshot:
    """Read-only snapshot of risk-context inputs for a single asset.

    Sampled at ``sampled_at`` (UTC). All numeric fields default safely to
    zero / ``None`` when no underlying data is available.
    """

    asset_id: uuid.UUID
    asset_symbol: str
    spread_bps: float
    daily_drawdown_pct: float
    recent_losses_count: int
    last_loss_at: Optional[datetime]
    sampled_at: datetime
    bar_observed: bool
    lookback_hours: int
    opened_by_filter: Optional[str]

    def to_dict(self) -> dict:
        return {
            "asset_id": str(self.asset_id),
            "asset_symbol": self.asset_symbol,
            "spread_bps": self.spread_bps,
            "daily_drawdown_pct": self.daily_drawdown_pct,
            "recent_losses_count": self.recent_losses_count,
            "last_loss_at": (
                self.last_loss_at.isoformat() if self.last_loss_at else None
            ),
            "sampled_at": self.sampled_at.isoformat(),
            "bar_observed": self.bar_observed,
            "lookback_hours": self.lookback_hours,
            "opened_by_filter": self.opened_by_filter,
        }


class MarketContextSnapshotService:
    """Read-only computer of ``MarketContextSnapshot`` rows.

    NOT wired into any production code path. Scaffolding only.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def snapshot(
        self,
        *,
        asset_id: uuid.UUID,
        asset_symbol: str,
        account_equity: float,
        lookback_hours: int = 24,
        opened_by_filter: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> MarketContextSnapshot:
        """Compute a ``MarketContextSnapshot`` for ``asset_id``.

        Parameters
        ----------
        asset_id : UUID
            Asset to compute the snapshot for.
        asset_symbol : str
            Symbol label (carried through; not validated against ``asset_id``).
        account_equity : float
            Used as the denominator for ``daily_drawdown_pct``. If
            non-positive, drawdown is reported as 0.0.
        lookback_hours : int, default 24
            Window for the recent-losses count. Must be >= 1.
        opened_by_filter : str, optional
            When provided, daily-drawdown and recent-losses queries only
            consider positions whose ``opened_by`` matches. Production
            usage will pass ``"auto_paper"`` so the auto-paper circuit
            breaker is not contaminated by manual or live trades.
        now : datetime, optional
            Override sampling time (testing). Must be timezone-aware UTC.
        """
        if lookback_hours < 1:
            raise ValueError("lookback_hours must be >= 1")

        sampled_at = now or datetime.now(timezone.utc)
        if sampled_at.tzinfo is None:
            raise ValueError("now must be timezone-aware (UTC)")

        spread_bps, bar_observed = self._compute_spread_bps(asset_id)
        daily_dd_pct = self._compute_daily_drawdown_pct(
            account_equity=account_equity,
            now=sampled_at,
            opened_by_filter=opened_by_filter,
        )
        losses_count, last_loss_at = self._compute_recent_losses(
            now=sampled_at,
            lookback_hours=lookback_hours,
            opened_by_filter=opened_by_filter,
        )

        return MarketContextSnapshot(
            asset_id=asset_id,
            asset_symbol=asset_symbol,
            spread_bps=spread_bps,
            daily_drawdown_pct=daily_dd_pct,
            recent_losses_count=losses_count,
            last_loss_at=last_loss_at,
            sampled_at=sampled_at,
            bar_observed=bar_observed,
            lookback_hours=lookback_hours,
            opened_by_filter=opened_by_filter,
        )

    # ------------------------------------------------------------------ #
    # Internal computers                                                 #
    # ------------------------------------------------------------------ #

    def _compute_spread_bps(self, asset_id: uuid.UUID) -> tuple[float, bool]:
        """Estimate spread in basis points from the most recent bar.

        Uses ``(high - low) / mid * 10_000`` as a proxy because we do not
        currently store top-of-book quotes for paper mode. Returns
        ``(0.0, False)`` when no bar exists or the mid is non-positive.
        """
        bar: Optional[Bar] = (
            self._session.execute(
                select(Bar)
                .where(Bar.asset_id == asset_id)
                .order_by(desc(Bar.ts))
                .limit(1)
            ).scalar_one_or_none()
        )
        if bar is None:
            return 0.0, False

        try:
            high = float(bar.high)
            low = float(bar.low)
        except (TypeError, ValueError):
            return 0.0, True

        mid = (high + low) / 2.0
        if mid <= 0.0 or high < low:
            return 0.0, True

        return ((high - low) / mid) * 10_000.0, True

    def _compute_daily_drawdown_pct(
        self,
        *,
        account_equity: float,
        now: datetime,
        opened_by_filter: Optional[str],
    ) -> float:
        """Return positive percentage of equity lost today via realized losses.

        Today is the UTC calendar day of ``now``. Only positions whose
        ``closed_at`` falls within today AND whose ``realized_pnl`` is
        negative contribute. Returns 0.0 when equity is non-positive or
        there are no qualifying losses.
        """
        if account_equity <= 0.0:
            return 0.0

        start_of_day = datetime(
            now.year, now.month, now.day, tzinfo=timezone.utc
        )
        end_of_day = start_of_day + timedelta(days=1)

        conditions = [
            Position.status == PositionStatus.CLOSED,
            Position.closed_at >= start_of_day,
            Position.closed_at < end_of_day,
            Position.realized_pnl < 0,
        ]
        if opened_by_filter is not None:
            conditions.append(Position.opened_by == opened_by_filter)

        total_negative = self._session.execute(
            select(func.coalesce(func.sum(Position.realized_pnl), 0)).where(
                and_(*conditions)
            )
        ).scalar_one()

        try:
            losses_abs = abs(float(total_negative or 0.0))
        except (TypeError, ValueError):
            return 0.0

        return (losses_abs / account_equity) * 100.0

    def _compute_recent_losses(
        self,
        *,
        now: datetime,
        lookback_hours: int,
        opened_by_filter: Optional[str],
    ) -> tuple[int, Optional[datetime]]:
        """Count closed losing positions within the lookback window.

        Returns ``(count, last_loss_closed_at)``. ``count`` is 0 and the
        timestamp is ``None`` when no qualifying rows exist.
        """
        cutoff = now - timedelta(hours=lookback_hours)

        conditions = [
            Position.status == PositionStatus.CLOSED,
            Position.closed_at >= cutoff,
            Position.realized_pnl < 0,
        ]
        if opened_by_filter is not None:
            conditions.append(Position.opened_by == opened_by_filter)

        count_val = self._session.execute(
            select(func.count(Position.id)).where(and_(*conditions))
        ).scalar_one()

        latest_ts = self._session.execute(
            select(func.max(Position.closed_at)).where(and_(*conditions))
        ).scalar_one()

        return int(count_val or 0), latest_ts
