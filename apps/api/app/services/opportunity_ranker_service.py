"""OpportunityRankerService — ranks recent CANDIDATE signals by composite score.

Ranking formula (all factors weighted 0-1, then combined):
  score = 0.40 * signal_score + 0.30 * confidence + 0.10 * catalyst_score
        + 0.20 * historical_win_rate  (setup × regime combination)

``historical_win_rate`` defaults to 0.50 (neutral prior) when fewer than
``_MIN_HISTORY_SAMPLES`` outcomes exist for the setup/regime combination.

Only signals with ``signal_status = CANDIDATE`` and ``should_trade = True``
(represented by ``signal_score >= 50``) are included by default.

The service is pure in-memory: it loads signals from the DB, computes ranks,
and returns a list of ``RankedOpportunity`` dataclasses.  No writes occur.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import AssetClass, SignalStatus
from app.db.models.asset import Asset
from app.db.models.signal import Signal
from app.services.runtime.scoring_service import ScoringService
from app.services.visual_seed import provider_filter

if TYPE_CHECKING:
    from app.services.performance_stats_service import PerformanceStatsService

# Neutral prior used when there is insufficient outcome history
_NEUTRAL_WIN_RATE = 0.50
# Minimum outcomes before the historical win rate replaces the neutral prior
_MIN_HISTORY_SAMPLES = 10

# Only consider signals generated within the last N hours
_RECENCY_HOURS = 8

# Minimum signal_score to be ranked (delegates to ScoringService)
_MIN_SIGNAL_SCORE = 50.0


@dataclass(frozen=True)
class RankedOpportunity:
    """A ranked trade setup ready for display or auto-paper execution."""

    signal_id: uuid.UUID
    asset: str
    asset_class: AssetClass
    direction: str
    setup_type: str
    confidence: float
    score: float
    regime: str
    horizon: str
    entry_low: float
    entry_high: float
    stop_price: float
    target_price: float


def _safe_float(value, default: float = 0.0) -> float:
    """Coerce Decimal / None to Python float."""
    if value is None:
        return default
    return float(value)


# Module-level ScoringService instance (stateless; safe to share)
_scoring_service = ScoringService()


class OpportunityRankerService:
    """Load and rank recent candidate signals.

    Parameters
    ----------
    session:
        Active SQLAlchemy session (read-only usage; no writes occur).
    performance_stats:
        Optional ``PerformanceStatsService`` used to load historical win rates.
        When *None*, all signals receive the neutral prior (0.50).
    """

    def __init__(
        self,
        session: Session,
        performance_stats: "PerformanceStatsService | None" = None,
        scoring_service: ScoringService | None = None,
    ) -> None:
        self._session = session
        self._performance_stats = performance_stats
        self._scoring = scoring_service or _scoring_service

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_win_rate_lookup(self) -> dict[str, float]:
        """Return a {setup_type_key: win_rate} dict from outcome history.

        Returns an empty dict when no PerformanceStatsService is injected or
        when there are insufficient samples (< _MIN_HISTORY_SAMPLES).
        """
        if self._performance_stats is None:
            return {}
        rows = self._performance_stats.win_rate_by_setup(min_samples=_MIN_HISTORY_SAMPLES)
        return {r.key: r.win_rate for r in rows}

    def rank(
        self,
        limit: int = 10,
        recency_hours: int = _RECENCY_HOURS,
        *,
        include_visual_seed: bool = False,
    ) -> list[RankedOpportunity]:
        """Return the top-ranked opportunities ordered by composite score (desc)."""
        cutoff = datetime.now(UTC) - timedelta(hours=recency_hours)

        rows = (
            self._session.execute(
                select(Signal, Asset)
                .join(Asset, Signal.asset_id == Asset.id)
                .where(Signal.signal_status == SignalStatus.CANDIDATE)
                .where(Signal.scan_ts >= cutoff)
                .where(Signal.signal_score >= _MIN_SIGNAL_SCORE)
                .where(provider_filter(Signal.provider_name, include_visual_seed=include_visual_seed))
                .order_by(Signal.signal_score.desc())
            )
            .all()
        )

        win_rate_lookup = self._build_win_rate_lookup()

        opportunities: list[tuple[float, RankedOpportunity]] = []
        for signal, asset in rows:
            setup_key = signal.setup_type.value if signal.setup_type else ""
            hist_wr = win_rate_lookup.get(setup_key, _NEUTRAL_WIN_RATE)
            score = self._scoring.composite_score(
                signal_score=_safe_float(signal.signal_score),
                confidence=_safe_float(signal.confidence),
                catalyst_score=_safe_float(signal.catalyst_score),
                historical_win_rate=hist_wr,
            )
            op = RankedOpportunity(
                signal_id=signal.id,
                asset=asset.symbol,
                asset_class=asset.asset_class,
                direction=signal.direction.value if signal.direction else "unknown",
                setup_type=setup_key or "unknown",
                confidence=_safe_float(signal.confidence),
                score=round(score, 2),
                regime=signal.regime.value if signal.regime else "unknown",
                horizon=signal.horizon_label.value if signal.horizon_label else "unknown",
                entry_low=_safe_float(signal.entry_min),
                entry_high=_safe_float(signal.entry_max),
                stop_price=_safe_float(signal.stop_price),
                target_price=_safe_float(signal.target_price),
            )
            opportunities.append((score, op))

        opportunities.sort(key=lambda t: t[0], reverse=True)
        return [op for _, op in opportunities[:limit]]
