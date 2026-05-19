"""Chart-pattern detection features — breakout, compression, etc."""

from __future__ import annotations

from typing import Sequence


def is_range_compressed(
    highs: Sequence[float],
    lows: Sequence[float],
    period: int = 10,
    threshold: float = 0.03,
) -> bool | None:
    """Return True if the high-low range over *period* bars is <= *threshold*."""
    if len(highs) < period:
        return None
    period_high = max(highs[-period:])
    period_low = min(lows[-period:])
    if period_low == 0:
        return None
    return (period_high - period_low) / period_low <= threshold


def is_breakout(
    closes: Sequence[float],
    highs: Sequence[float],
    lookback: int = 20,
) -> bool | None:
    """Return True if the latest close breaks above the *lookback*-bar high."""
    if len(closes) < lookback + 1 or len(highs) < lookback + 1:
        return None
    recent_high = max(highs[-(lookback + 1):-1])
    return closes[-1] > recent_high
