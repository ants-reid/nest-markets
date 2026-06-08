"""Deterministic market regime preclassification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeResult:
    """Market regime classification result."""

    regime: str
    confidence: float


def classify_regime(*args, **kwargs):
    """Classify regime with compatibility across legacy/new call signatures."""
    if "trend_score" in kwargs:
        trend_score = float(kwargs.get("trend_score", 0.0))
        volatility = float(kwargs.get("volatility", 0.0))
        adx = float(kwargs.get("adx") or 0.0)

        if volatility >= 0.035:
            return "high_volatility"
        if abs(trend_score) >= 0.2 and adx >= 20.0:
            return "trend"
        return "range"

    adx = float(args[0]) if len(args) > 0 else float(kwargs.get("adx", 0.0))
    rsi = float(args[1]) if len(args) > 1 else float(kwargs.get("rsi", 50.0))
    volatility = float(args[2]) if len(args) > 2 else float(kwargs.get("volatility", 0.0))
    trend_direction = str(args[3]) if len(args) > 3 else str(kwargs.get("trend_direction", "neutral"))
    trend_strength = float(args[4]) if len(args) > 4 else float(kwargs.get("trend_strength", 0.0))

    if volatility >= 0.04:
        return RegimeResult(regime="high_vol", confidence=min(volatility / 0.05, 1.0))
    if volatility <= 0.006:
        return RegimeResult(regime="low_vol", confidence=0.7)
    if adx >= 25.0 and trend_strength >= 0.5:
        if trend_direction == "up":
            confidence = min(adx / 50.0 + trend_strength * 0.4, 1.0)
            return RegimeResult(regime="trending_up", confidence=confidence)
        if trend_direction == "down":
            confidence = min(adx / 50.0 + trend_strength * 0.4, 1.0)
            return RegimeResult(regime="trending_down", confidence=confidence)
    if adx < 20.0 and (rsi > 70.0 or rsi < 30.0):
        return RegimeResult(regime="mean_reversion", confidence=0.6)
    return RegimeResult(regime="ranging", confidence=0.5)


def assess_market_quality(*args, **kwargs):
    """Assess market quality with compatibility for both bool and string callers."""
    if "liquidity_score" in kwargs or "volatility_score" in kwargs:
        liquidity_score = float(kwargs.get("liquidity_score", 0.0))
        volatility_score = float(kwargs.get("volatility_score", 0.0))
        return liquidity_score >= 20.0 and volatility_score >= 20.0

    spread_bps = float(args[0]) if len(args) > 0 else float(kwargs.get("spread_bps", 999.0))
    if spread_bps < 2.0:
        return "good"
    if spread_bps < 6.0:
        return "fair"
    return "poor"
