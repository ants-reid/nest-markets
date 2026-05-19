"""Bid/ask spread metrics for execution quality assessment."""

from __future__ import annotations


def absolute_spread(bid: float, ask: float) -> float:
    """Return the absolute bid/ask spread."""
    return ask - bid


def relative_spread(bid: float, ask: float) -> float | None:
    """Return the spread as a fraction of the mid-price."""
    mid = (bid + ask) / 2
    if mid == 0:
        return None
    return (ask - bid) / mid


def spread_regime(relative_spread_value: float) -> str:
    """Classify the spread as 'tight', 'normal', or 'wide'."""
    if relative_spread_value < 0.001:
        return "tight"
    if relative_spread_value < 0.005:
        return "normal"
    return "wide"
