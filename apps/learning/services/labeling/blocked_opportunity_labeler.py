"""BlockedOpportunityLabeler — label opportunities blocked by risk controls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlockedOpportunityRecord:
    """An opportunity blocked before execution."""

    opportunity_id: str
    symbol: str
    block_reason: str       # e.g. "max_open_positions", "daily_loss_limit"
    score_at_block: float
    would_have_won: bool | None  # None if unknown (no forward data yet)


@dataclass(frozen=True)
class BlockedOpportunityLabel:
    """Learning label for a blocked opportunity."""

    opportunity_id: str
    block_reason: str
    score_at_block: float
    block_quality: str  # "correct_block", "missed_win", "avoided_loss", "unknown"


class BlockedOpportunityLabeler:
    """Assess whether a risk block was correct in hindsight."""

    def label(self, record: BlockedOpportunityRecord) -> BlockedOpportunityLabel:
        if record.would_have_won is None:
            quality = "unknown"
        elif record.would_have_won:
            quality = "missed_win"
        else:
            quality = "avoided_loss" if record.score_at_block < 0.65 else "correct_block"

        return BlockedOpportunityLabel(
            opportunity_id=record.opportunity_id,
            block_reason=record.block_reason,
            score_at_block=record.score_at_block,
            block_quality=quality,
        )
