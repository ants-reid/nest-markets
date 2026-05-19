"""Yield curve features — slope and inversion detection."""

from __future__ import annotations


def yield_curve_slope(short_rate: float, long_rate: float) -> float:
    """Return long_rate minus short_rate (positive = normal, negative = inverted)."""
    return long_rate - short_rate


def is_inverted(short_rate: float, long_rate: float) -> bool:
    """Return True if the yield curve is inverted (short > long)."""
    return short_rate > long_rate


def curve_steepness_regime(slope: float) -> str:
    """Classify the curve as 'inverted', 'flat', or 'steep'."""
    if slope < -0.25:
        return "inverted"
    if slope < 0.50:
        return "flat"
    return "steep"
