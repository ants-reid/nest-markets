"""ForwardReturnLabeler — compute forward returns for a given holding period."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ForwardReturnLabel:
    """Forward return label for a signal or opportunity."""

    signal_id: str
    holding_period_bars: int
    forward_return: float     # as decimal fraction
    forward_return_pct: float # same, as percentage
    hit: bool                 # True if return > threshold


class ForwardReturnLabeler:
    """Compute forward returns for signals/opportunities."""

    def __init__(self, win_threshold: float = 0.02) -> None:
        self._threshold = win_threshold

    def label(
        self,
        signal_id: str,
        prices: Sequence[float],
        holding_period: int,
        side: str = "long",
    ) -> ForwardReturnLabel | None:
        """Return a ForwardReturnLabel, or None if insufficient price data."""
        if len(prices) < holding_period + 1:
            return None
        entry = prices[0]
        exit_price = prices[holding_period]
        if entry == 0:
            return None
        if side == "long":
            fwd = (exit_price - entry) / entry
        else:
            fwd = (entry - exit_price) / entry
        return ForwardReturnLabel(
            signal_id=signal_id,
            holding_period_bars=holding_period,
            forward_return=fwd,
            forward_return_pct=fwd * 100,
            hit=fwd >= self._threshold,
        )
