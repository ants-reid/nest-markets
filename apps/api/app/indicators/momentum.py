"""Deterministic momentum scoring helpers."""

from collections.abc import Sequence
from dataclasses import dataclass


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class ROCResult:
    """Rate of change result."""

    value: float | None
    direction: str
    strength: float


@dataclass(frozen=True)
class MomentumScoreResult:
    """Composite momentum score result."""

    value: float | None
    direction: str
    strength: float


def calculate_momentum(current_price: float, price_n_bars_ago: float) -> float:
    """Compute simple relative move in percent."""
    if price_n_bars_ago <= 0.0:
        return 0.0
    return ((current_price / price_n_bars_ago) - 1.0) * 100.0


def calculate_roc(prices: Sequence[float], period: int = 12) -> ROCResult:
    """Compute rate of change with direction and strength."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(prices) < period + 1:
        return ROCResult(value=None, direction="neutral", strength=0.0)
    baseline = prices[-period - 1]
    if baseline <= 0.0:
        return ROCResult(value=None, direction="neutral", strength=0.0)
    roc_value = ((prices[-1] / baseline) - 1.0) * 100.0
    if roc_value > 1.0:
        direction = "bullish"
    elif roc_value < -1.0:
        direction = "bearish"
    else:
        direction = "neutral"
    strength = _clamp(abs(roc_value) / 20.0, 0.0, 1.0)
    return ROCResult(value=roc_value, direction=direction, strength=strength)


def calculate_momentum_score(
    rsi: float,
    roc: float,
    adx: float,
) -> MomentumScoreResult:
    """Compute composite momentum score from RSI, ROC, and ADX.

    Returns a MomentumScoreResult with direction and normalised strength.
    """
    # Normalise inputs to [-1, 1] components
    rsi_component = _clamp((rsi - 50.0) / 30.0, -1.0, 1.0)
    roc_component = _clamp(roc / 10.0, -1.0, 1.0)
    adx_component = _clamp((adx - 25.0) / 25.0, 0.0, 1.0)  # ADX adds magnitude not sign

    # Blend: RSI 40%, ROC 40%, ADX 20%
    raw_score = (0.4 * rsi_component) + (0.4 * roc_component) + (0.2 * adx_component * (1.0 if rsi_component >= 0 else -1.0))
    value = _clamp(raw_score, -1.0, 1.0)

    if value > 0.1:
        direction = "bullish"
    elif value < -0.1:
        direction = "bearish"
    else:
        direction = "neutral"

    strength = _clamp(abs(value), 0.0, 1.0)
    return MomentumScoreResult(value=value, direction=direction, strength=strength)


def _calculate_momentum_score_from_prices(prices: Sequence[float], lookback: int = 10) -> float | None:
    """Legacy momentum score from price series (internal use)."""
    if lookback <= 1:
        raise ValueError("lookback must be greater than 1")
    if len(prices) < lookback + 1:
        return None

    recent = prices[-(lookback + 1):]
    total_move_pct = calculate_momentum(recent[-1], recent[0]) / 100.0

    returns: list[float] = []
    for idx in range(1, len(recent)):
        previous = recent[idx - 1]
        if previous <= 0.0:
            return None
        returns.append((recent[idx] / previous) - 1.0)

    avg_return = sum(returns) / float(len(returns))
    total_component = _clamp(total_move_pct / 0.05, -1.0, 1.0)
    avg_component = _clamp(avg_return / 0.01, -1.0, 1.0)
    return _clamp((0.7 * total_component) + (0.3 * avg_component), -1.0, 1.0)
