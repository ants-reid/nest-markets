"""Market breadth features — advance/decline, new highs/lows."""

from __future__ import annotations

from typing import Sequence


def advance_decline_ratio(advances: int, declines: int) -> float | None:
    """Return A/D ratio.  Returns None if declines is zero."""
    if declines == 0:
        return None
    return advances / declines


def breadth_thrust(
    advances_series: Sequence[int],
    total_series: Sequence[int],
    period: int = 10,
) -> float | None:
    """Zweig Breadth Thrust: 10-day EMA of (advances / total issues).

    Returns the latest EMA value, or None if insufficient data.
    """
    if len(advances_series) < period or len(total_series) < period:
        return None
    ratios = [
        a / t if t > 0 else 0.0
        for a, t in zip(advances_series[-period:], total_series[-period:])
    ]
    # Simple EMA over the period
    k = 2 / (period + 1)
    ema = ratios[0]
    for r in ratios[1:]:
        ema = r * k + ema * (1 - k)
    return ema
