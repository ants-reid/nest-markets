"""Deterministic RSI implementation using Wilder smoothing."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RSIResult:
    """RSI computation result."""

    value: float | None
    period: int

    def _as_float(self) -> float:
        return float(self.value) if self.value is not None else 0.0

    def __float__(self) -> float:
        return self._as_float()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (int, float)):
            return self._as_float() == float(other)
        return super().__eq__(other)

    def __lt__(self, other: float) -> bool:
        return self._as_float() < float(other)

    def __le__(self, other: float) -> bool:
        return self._as_float() <= float(other)

    def __gt__(self, other: float) -> bool:
        return self._as_float() > float(other)

    def __ge__(self, other: float) -> bool:
        return self._as_float() >= float(other)


def calculate_rsi(prices: Sequence[float], period: int = 14) -> RSIResult:
    """Compute RSI from close prices.

    Returns:
        RSIResult with value in range [0, 100], or None when data is insufficient.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if len(prices) < period + 1:
        return RSIResult(value=None, period=period)

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(delta, 0.0) for delta in deltas]
    losses = [max(-delta, 0.0) for delta in deltas]

    avg_gain = sum(gains[:period]) / float(period)
    avg_loss = sum(losses[:period]) / float(period)

    for idx in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[idx]) / float(period)
        avg_loss = ((avg_loss * (period - 1)) + losses[idx]) / float(period)

    if avg_loss == 0.0:
        raw = 100.0 if avg_gain > 0.0 else 50.0
    else:
        rs = avg_gain / avg_loss
        raw = 100.0 - (100.0 / (1.0 + rs))

    return RSIResult(value=raw, period=period)


def calculate_smoothed_rsi(prices: Sequence[float], period: int = 14) -> RSIResult:
    """Compatibility alias for Wilder RSI."""
    return calculate_rsi(prices, period)
