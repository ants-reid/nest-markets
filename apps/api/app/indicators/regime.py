"""Deterministic market regime preclassification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeResult:
    """Market regime classification result."""

    regime: str
    confidence: float


def classify_regime(
    adx: float,
    rsi: float,
    volatility: float,
    trend_direction: str,
    trend_strength: float,
) -> RegimeResult:
    """Classify market regime from indicator inputs.

    Returns a RegimeResult with regime label and confidence score.

    Regime labels: trending_up, trending_down, mean_reversion, high_vol, low_vol, ranging.
    """
    # High volatility regime
    if volatility >= 0.04:
        return RegimeResult(regime="high_vol", confidence=min(volatility / 0.05, 1.0))

    # Low volatility regime
    if volatility <= 0.006:
        return RegimeResult(regime="low_vol", confidence=0.7)

    # Trending regimes
    if adx >= 25.0 and trend_strength >= 0.5:
        if trend_direction == "up":
            confidence = min(adx / 50.0 + trend_strength * 0.4, 1.0)
            return RegimeResult(regime="trending_up", confidence=confidence)
        if trend_direction == "down":
            confidence = min(adx / 50.0 + trend_strength * 0.4, 1.0)
            return RegimeResult(regime="trending_down", confidence=confidence)

    # Mean reversion (low ADX, extreme RSI)
    if adx < 20.0 and (rsi > 70.0 or rsi < 30.0):
        return RegimeResult(regime="mean_reversion", confidence=0.6)

    # Ranging
    return RegimeResult(regime="ranging", confidence=0.5)


def assess_market_quality(
    spread_bps: float,
    volatility: float,
    volume_ratio: float,
) -> str:
    """Assess market quality from spread, volatility, and volume.

    Returns "good", "fair", or "poor".
    """
    if spread_bps < 2.0:
        return "good"
    if spread_bps < 6.0:
        return "fair"
    return "poor"
