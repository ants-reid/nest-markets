"""Volume analysis features."""

from __future__ import annotations

from typing import Sequence


def relative_volume(
    volumes: Sequence[float],
    period: int = 20,
) -> float | None:
    """Return latest volume divided by the average volume over *period* bars.

    Values > 1.0 indicate above-average volume.
    """
    if len(volumes) < period + 1:
        return None
    avg = sum(volumes[-(period + 1):-1]) / period
    if avg == 0:
        return None
    return volumes[-1] / avg


def volume_trend(volumes: Sequence[float], period: int = 5) -> float | None:
    """Return the linear slope of volume over *period* bars (normalised by mean)."""
    if len(volumes) < period:
        return None
    window = list(volumes[-period:])
    mean = sum(window) / period
    if mean == 0:
        return None
    xs = list(range(period))
    x_mean = (period - 1) / 2
    numerator = sum((xs[i] - x_mean) * (window[i] - mean) for i in range(period))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return (numerator / denominator) / mean
