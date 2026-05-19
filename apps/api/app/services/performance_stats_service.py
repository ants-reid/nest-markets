"""PerformanceStatsService — aggregate win rates from signal outcome history.

Computes overall and per-dimension win rates from the signal_outcomes table.
All methods accept an optional ``min_samples`` threshold; dimensions with fewer
outcomes than the threshold are excluded from the response.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.signal import Signal
from app.db.models.signal_outcome import SignalOutcome
from app.services.visual_seed import provider_filter

# Default minimum sample size before reporting a statistic
DEFAULT_MIN_SAMPLES = 1


@dataclass(frozen=True)
class DimensionWinRate:
    """Win rate for a single analysis dimension (setup, asset, regime, etc.)."""

    key: str
    total: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class PerformanceStats:
    """Aggregate performance statistics snapshot."""

    total_trades: int
    total_wins: int
    overall_win_rate: float
    by_setup: list[DimensionWinRate] = field(default_factory=list)
    by_asset: list[DimensionWinRate] = field(default_factory=list)
    by_catalyst: list[DimensionWinRate] = field(default_factory=list)
    by_regime: list[DimensionWinRate] = field(default_factory=list)


def _win_rate(wins: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(wins / total, 4)


class PerformanceStatsService:
    """Load and aggregate signal outcome stats for the AI learning loop."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public aggregation methods
    # ------------------------------------------------------------------

    def overall_stats(
        self,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        *,
        include_visual_seed: bool = False,
    ) -> PerformanceStats:
        """Return full stats breakdown; dimensions below min_samples are omitted."""
        total, wins = self._overall_count(include_visual_seed=include_visual_seed)
        return PerformanceStats(
            total_trades=total,
            total_wins=wins,
            overall_win_rate=_win_rate(wins, total),
            by_setup=self.win_rate_by_setup(min_samples, include_visual_seed=include_visual_seed),
            by_asset=self.win_rate_by_asset(min_samples, include_visual_seed=include_visual_seed),
            by_catalyst=self.win_rate_by_catalyst(min_samples, include_visual_seed=include_visual_seed),
            by_regime=self.win_rate_by_regime(min_samples, include_visual_seed=include_visual_seed),
        )

    def win_rate_by_setup(
        self,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        *,
        include_visual_seed: bool = False,
    ) -> list[DimensionWinRate]:
        """Per-setup win rates with at least min_samples outcomes."""
        rows = (
            self._session.execute(
                select(
                    SignalOutcome.setup_type,
                    func.count().label("total"),
                    func.sum(
                        func.cast(SignalOutcome.predicted_direction_correct, func.count().type)
                    ).label("wins"),
                )
                .join(Signal, SignalOutcome.signal_id == Signal.id)
                .where(SignalOutcome.predicted_direction_correct.is_not(None))
                .where(provider_filter(Signal.provider_name, include_visual_seed=include_visual_seed))
                .group_by(SignalOutcome.setup_type)
            ).all()
        )
        return self._to_dimension(rows, min_samples)

    def win_rate_by_asset(
        self,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        *,
        include_visual_seed: bool = False,
    ) -> list[DimensionWinRate]:
        """Per-asset win rates keyed by symbol."""
        rows = (
            self._session.execute(
                select(
                    Asset.symbol,
                    func.count().label("total"),
                    func.sum(
                        func.cast(SignalOutcome.predicted_direction_correct, func.count().type)
                    ).label("wins"),
                )
                .join(Signal, SignalOutcome.signal_id == Signal.id)
                .join(Asset, SignalOutcome.asset_id == Asset.id)
                .where(SignalOutcome.predicted_direction_correct.is_not(None))
                .where(provider_filter(Signal.provider_name, include_visual_seed=include_visual_seed))
                .group_by(Asset.symbol)
            ).all()
        )
        return self._to_dimension(rows, min_samples)

    def win_rate_by_catalyst(
        self,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        *,
        include_visual_seed: bool = False,
    ) -> list[DimensionWinRate]:
        """Per-catalyst-type win rates."""
        rows = (
            self._session.execute(
                select(
                    SignalOutcome.catalyst_type,
                    func.count().label("total"),
                    func.sum(
                        func.cast(SignalOutcome.predicted_direction_correct, func.count().type)
                    ).label("wins"),
                )
                .join(Signal, SignalOutcome.signal_id == Signal.id)
                .where(SignalOutcome.predicted_direction_correct.is_not(None))
                .where(provider_filter(Signal.provider_name, include_visual_seed=include_visual_seed))
                .group_by(SignalOutcome.catalyst_type)
            ).all()
        )
        return self._to_dimension(rows, min_samples)

    def win_rate_by_regime(
        self,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        *,
        include_visual_seed: bool = False,
    ) -> list[DimensionWinRate]:
        """Per-regime win rates."""
        rows = (
            self._session.execute(
                select(
                    SignalOutcome.regime_at_entry,
                    func.count().label("total"),
                    func.sum(
                        func.cast(SignalOutcome.predicted_direction_correct, func.count().type)
                    ).label("wins"),
                )
                .join(Signal, SignalOutcome.signal_id == Signal.id)
                .where(SignalOutcome.predicted_direction_correct.is_not(None))
                .where(provider_filter(Signal.provider_name, include_visual_seed=include_visual_seed))
                .group_by(SignalOutcome.regime_at_entry)
            ).all()
        )
        return self._to_dimension(rows, min_samples)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _overall_count(self, *, include_visual_seed: bool = False) -> tuple[int, int]:
        row = self._session.execute(
            select(
                func.count().label("total"),
                func.sum(
                    func.cast(SignalOutcome.predicted_direction_correct, func.count().type)
                ).label("wins"),
            )
            .join(Signal, SignalOutcome.signal_id == Signal.id)
            .where(SignalOutcome.predicted_direction_correct.is_not(None))
            .where(provider_filter(Signal.provider_name, include_visual_seed=include_visual_seed))
        ).one()
        return int(row.total or 0), int(row.wins or 0)

    @staticmethod
    def _to_dimension(rows: Sequence, min_samples: int) -> list[DimensionWinRate]:
        result: list[DimensionWinRate] = []
        for row in rows:
            total = int(row.total or 0)
            if total < min_samples:
                continue
            wins = int(row.wins or 0)
            key_val = row[0]
            key = key_val.value if hasattr(key_val, "value") else str(key_val)
            result.append(
                DimensionWinRate(
                    key=key,
                    total=total,
                    wins=wins,
                    win_rate=_win_rate(wins, total),
                )
            )
        return sorted(result, key=lambda r: r.win_rate, reverse=True)
