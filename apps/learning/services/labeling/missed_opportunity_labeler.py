"""MissedOpportunityLabeler — label opportunities that were not taken."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissedOpportunityRecord:
    """Represents an opportunity that existed but was not executed."""

    opportunity_id: str
    symbol: str
    signal_price: float     # price at signal generation
    peak_price: float       # best price after signal
    side: str               # "long" or "short"
    reason_missed: str      # e.g. "blocked_by_risk", "no_position_available"


@dataclass(frozen=True)
class MissedOpportunityLabel:
    """Learning label for a missed opportunity."""

    opportunity_id: str
    forgone_pnl_pct: float  # % gain that was left on the table
    missed_regime: str      # qualitative: "small_miss", "large_miss"
    reason_missed: str


class MissedOpportunityLabeler:
    """Compute learning labels for opportunities that were not traded."""

    def label(self, record: MissedOpportunityRecord) -> MissedOpportunityLabel:
        if record.side == "long":
            forgone_pct = (record.peak_price - record.signal_price) / record.signal_price
        else:
            forgone_pct = (record.signal_price - record.peak_price) / record.signal_price

        if forgone_pct >= 0.05:
            regime = "large_miss"
        elif forgone_pct >= 0.01:
            regime = "small_miss"
        else:
            regime = "negligible"

        return MissedOpportunityLabel(
            opportunity_id=record.opportunity_id,
            forgone_pnl_pct=forgone_pct,
            missed_regime=regime,
            reason_missed=record.reason_missed,
        )
