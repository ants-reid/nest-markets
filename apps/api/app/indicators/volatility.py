"""Deterministic volatility calculations."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

_ANNUALIZATION_FACTOR = math.sqrt(252.0)


@dataclass(frozen=True)
class VolatilityResult:
    """Volatility computation result."""

    value: float | None
    annualized: float | None


def calculate_realized_volatility(prices: Sequence[float], period: int = 20) -> VolatilityResult:
    """Compute close-to-close realized volatility.

    Returns the standard deviation of simple returns over the lookback window.
    """
    if period <= 1:
        raise ValueError("period must be greater than 1")
    if len(prices) < period + 1:
        return VolatilityResult(value=None, annualized=None)

    returns: list[float] = []
    for idx in range(len(prices) - period, len(prices)):
        previous = prices[idx - 1]
        current = prices[idx]
        if previous <= 0.0:
            return VolatilityResult(value=None, annualized=None)
        returns.append((current / previous) - 1.0)

    mean_return = sum(returns) / float(len(returns))
    variance = sum((ret - mean_return) ** 2 for ret in returns) / float(len(returns))
    vol = math.sqrt(variance)
    return VolatilityResult(value=vol, annualized=vol * _ANNUALIZATION_FACTOR)


def calculate_parkinson_volatility(
    bars: Sequence[dict[str, float]], period: int = 20
) -> VolatilityResult:
    """Compute Parkinson volatility from high/low ranges."""
    if period <= 1:
        raise ValueError("period must be greater than 1")
    if len(bars) < period:
        return VolatilityResult(value=None, annualized=None)

    squared_logs: list[float] = []
    for bar in bars[-period:]:
        high = float(bar["high"])
        low = float(bar["low"])
        if low <= 0.0 or high <= 0.0:
            return VolatilityResult(value=None, annualized=None)
        squared_logs.append(math.log(high / low) ** 2)

    mean_squared = sum(squared_logs) / float(len(squared_logs))
    vol = math.sqrt(mean_squared / (4.0 * math.log(2.0)))
    return VolatilityResult(value=vol, annualized=vol * _ANNUALIZATION_FACTOR)
