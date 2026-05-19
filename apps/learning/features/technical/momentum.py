"""Momentum features — multi-timeframe price momentum calculations."""

from __future__ import annotations

from typing import Sequence


def rate_of_change(prices: Sequence[float], period: int) -> float | None:
    """Return the rate-of-change over *period* bars as a decimal fraction.

    Returns None if there are not enough data points.
    """
    if len(prices) < period + 1:
        return None
    return (prices[-1] - prices[-(period + 1)]) / prices[-(period + 1)]


def momentum_score(
    prices: Sequence[float],
    periods: tuple[int, ...] = (5, 21, 63),
) -> dict[str, float | None]:
    """Return ROC for each period in *periods* keyed as ``roc_{period}``."""
    return {f"roc_{p}": rate_of_change(prices, p) for p in periods}
