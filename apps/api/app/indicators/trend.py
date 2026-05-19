"""Deterministic trend scoring helpers."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.indicators.ema import calculate_ema


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class TrendResult:
    """Structured trend assessment from SMA inputs."""

    direction: str
    strength: float
    duration_bars: int


def calculate_trend_score_from_prices(
    prices: Sequence[float],
    fast_period: int = 20,
    slow_period: int = 50,
    slope_lookback: int = 5,
) -> float | None:
    """Compute EMA-based trend score in range [-1, 1].

    The score blends:
    - EMA fast vs EMA slow relative position,
    - slow EMA slope,
    - latest close vs slow EMA position.
    """
    if fast_period <= 0 or slow_period <= 0 or slope_lookback <= 0:
        raise ValueError("periods must be positive")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be smaller than slow_period")

    min_points = slow_period + slope_lookback
    if len(prices) < min_points:
        return None

    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)
    ema_slow_prev = calculate_ema(prices[:-slope_lookback], slow_period)

    if ema_fast is None or ema_slow is None or ema_slow_prev is None or ema_slow == 0.0:
        return None

    relative_gap = (ema_fast - ema_slow) / abs(ema_slow)
    slope = (ema_slow - ema_slow_prev) / abs(ema_slow_prev) if ema_slow_prev != 0.0 else 0.0
    price_position = (prices[-1] - ema_slow) / abs(ema_slow)

    position_component = _clamp(relative_gap / 0.03, -1.0, 1.0)
    slope_component = _clamp(slope / 0.02, -1.0, 1.0)
    price_component = _clamp(price_position / 0.03, -1.0, 1.0)

    score = (0.5 * position_component) + (0.3 * slope_component) + (0.2 * price_component)
    return _clamp(score, -1.0, 1.0)


def calculate_trend_direction(
    sma_short: float,
    sma_medium: float,
    sma_long: float,
    current_price: float,
) -> str:
    """Classify trend direction from SMA alignment and price position."""
    if sma_short > sma_medium and sma_medium > sma_long and current_price > sma_short:
        return "up"
    if sma_short < sma_medium and sma_medium < sma_long and current_price < sma_short:
        return "down"
    # Partial alignment — check short vs long
    gap_pct = (sma_short - sma_long) / abs(sma_long) if sma_long != 0.0 else 0.0
    if gap_pct > 0.03:
        return "up"
    if gap_pct < -0.03:
        return "down"
    return "neutral"


def calculate_trend_strength(
    sma_short: float,
    sma_medium: float,
    sma_long: float,
) -> float:
    """Calculate normalised trend strength in [0, 1] from SMA spread."""
    if sma_long == 0.0:
        return 0.0
    gap = abs(sma_short - sma_long) / abs(sma_long)
    return _clamp(gap / 0.08, 0.0, 1.0)


def calculate_trend_score(
    sma_short: float,
    sma_medium: float,
    sma_long: float,
    current_price: float,
    bars_up: int = 0,
    bars_down: int = 0,
) -> TrendResult:
    """Compute structured trend result from SMA inputs."""
    direction = calculate_trend_direction(sma_short, sma_medium, sma_long, current_price)
    strength = calculate_trend_strength(sma_short, sma_medium, sma_long)
    duration_bars = bars_up if direction == "up" else (bars_down if direction == "down" else 0)
    return TrendResult(direction=direction, strength=strength, duration_bars=duration_bars)
