"""Volatility features — ATR and realised volatility."""

from __future__ import annotations

import math
from typing import Sequence


def true_range(high: float, low: float, prev_close: float) -> float:
    """Standard True Range calculation."""
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def average_true_range(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> float | None:
    """Return the ATR over *period* bars, or None if insufficient data."""
    if len(highs) < period + 1:
        return None
    trs = [
        true_range(highs[i], lows[i], closes[i - 1])
        for i in range(1, len(highs))
    ]
    return sum(trs[-period:]) / period


def realised_volatility(
    closes: Sequence[float],
    period: int = 21,
    annualise: bool = True,
) -> float | None:
    """Return realised log-return volatility over *period* bars."""
    if len(closes) < period + 1:
        return None
    log_returns = [
        math.log(closes[i] / closes[i - 1])
        for i in range(len(closes) - period, len(closes))
    ]
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
    vol = math.sqrt(variance)
    return vol * math.sqrt(252) if annualise else vol
