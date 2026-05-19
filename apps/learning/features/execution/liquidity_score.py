"""Execution liquidity score."""

from __future__ import annotations


def liquidity_score(
    volume: float,
    spread: float,
    avg_daily_volume: float,
) -> float:
    """Return a 0–1 liquidity score.

    Higher is more liquid.  Combines relative volume and spread.
    """
    if avg_daily_volume == 0:
        return 0.0
    volume_factor = min(volume / avg_daily_volume, 1.0)
    spread_factor = max(0.0, 1.0 - spread * 200)  # penalise spreads above 0.5%
    return (volume_factor + spread_factor) / 2
