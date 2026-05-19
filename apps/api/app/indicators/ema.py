"""Deterministic exponential moving average helpers."""

from collections.abc import Sequence


def calculate_ema(prices: Sequence[float], period: int) -> float | None:
    """Compute the latest exponential moving average value.

    Args:
        prices: Price series in chronological order.
        period: EMA lookback period.

    Returns:
        Latest EMA value, or None when data is insufficient.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if len(prices) < period:
        return None

    multiplier = 2.0 / (period + 1.0)
    ema_value = sum(prices[:period]) / float(period)

    for price in prices[period:]:
        ema_value = (price - ema_value) * multiplier + ema_value

    return ema_value


def calculate_multiple_emas(
    prices: Sequence[float], periods: Sequence[int]
) -> dict[int, float | None]:
    """Compute multiple EMA values from the same price series."""
    return {period: calculate_ema(prices, period) for period in periods}
