"""Support/resistance and VWAP level features."""

from __future__ import annotations

from typing import Sequence


def pivot_high(highs: Sequence[float], window: int = 5) -> float | None:
    """Return the highest high in the last *window* bars, or None."""
    if len(highs) < window:
        return None
    return max(highs[-window:])


def pivot_low(lows: Sequence[float], window: int = 5) -> float | None:
    """Return the lowest low in the last *window* bars, or None."""
    if len(lows) < window:
        return None
    return min(lows[-window:])


def distance_from_high(price: float, highs: Sequence[float], window: int = 52) -> float | None:
    """Return fractional distance from the 52-week high."""
    high = pivot_high(highs, window)
    if high is None or high == 0:
        return None
    return (price - high) / high


def vwap(
    closes: Sequence[float],
    volumes: Sequence[float],
) -> float | None:
    """Return the volume-weighted average price."""
    if not closes or not volumes or len(closes) != len(volumes):
        return None
    total_volume = sum(volumes)
    if total_volume == 0:
        return None
    return sum(c * v for c, v in zip(closes, volumes)) / total_volume
