"""TradedOutcomeLabeler — label executed trade outcomes for learning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TradeRecord:
    """Minimal representation of a completed trade."""

    trade_id: str
    symbol: str
    entry_price: float
    exit_price: float
    side: str  # "long" or "short"
    quantity: float


@dataclass(frozen=True)
class TradedOutcomeLabel:
    """Learning label for an executed trade."""

    trade_id: str
    pnl: float
    pnl_pct: float
    r_multiple: float | None  # pnl / initial_risk; None if risk unknown
    outcome: str  # "win", "loss", "breakeven"


class TradedOutcomeLabeler:
    """Compute learning labels for trades that were actually executed."""

    def label(
        self,
        trade: TradeRecord,
        initial_risk: float | None = None,
    ) -> TradedOutcomeLabel:
        """Compute label for a single trade record."""
        if trade.side == "long":
            pnl = (trade.exit_price - trade.entry_price) * trade.quantity
        else:
            pnl = (trade.entry_price - trade.exit_price) * trade.quantity

        pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price
        if trade.side == "short":
            pnl_pct = -pnl_pct

        r_multiple = None
        if initial_risk and initial_risk != 0:
            r_multiple = pnl / initial_risk

        if pnl > 0:
            outcome = "win"
        elif pnl < 0:
            outcome = "loss"
        else:
            outcome = "breakeven"

        return TradedOutcomeLabel(
            trade_id=trade.trade_id,
            pnl=pnl,
            pnl_pct=pnl_pct,
            r_multiple=r_multiple,
            outcome=outcome,
        )

    def label_batch(
        self,
        trades: Sequence[TradeRecord],
        initial_risk: float | None = None,
    ) -> list[TradedOutcomeLabel]:
        return [self.label(t, initial_risk) for t in trades]
