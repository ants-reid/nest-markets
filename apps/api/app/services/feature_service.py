"""Deterministic feature assembly service.

This module assembles indicator outputs into a typed feature snapshot payload.
It intentionally does not perform any database writes.
"""

from dataclasses import dataclass
from typing import Any

from app.indicators.adx import calculate_adx
from app.indicators.atr import calculate_atr
from app.indicators.ema import calculate_ema
from app.indicators.liquidity import assess_liquidity_from_quote
from app.indicators.momentum import calculate_momentum_score
from app.indicators.regime import assess_market_quality, classify_regime
from app.indicators.rsi import calculate_rsi
from app.indicators.trend import calculate_trend_score
from app.indicators.volatility import calculate_realized_volatility


@dataclass(frozen=True)
class BarInput:
    """OHLCV input used by the feature engine."""

    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class QuoteInput:
    """Quote input used by liquidity scoring."""

    bid: float
    ask: float
    bid_size: float | None = None
    ask_size: float | None = None


@dataclass(frozen=True)
class FeatureInput:
    """Input payload for deterministic feature computation."""

    bars: list[BarInput]
    quotes: list[QuoteInput] | None = None
    context: dict[str, Any] | None = None


@dataclass(frozen=True)
class FeatureSnapshotPayload:
    """Structured feature result returned by the feature engine."""

    ema_fast: float | None
    ema_slow: float | None
    rsi: float | None
    atr: float | None
    adx: float | None
    volatility_score: float
    liquidity_score: float
    trend_score: float
    momentum_score: float
    regime_preclassification: str
    market_quality_flag: bool


def _to_bar_lists(bars: list[BarInput]) -> tuple[list[float], list[float], list[float]]:
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    closes = [bar.close for bar in bars]
    return highs, lows, closes


def _normalize_volatility(volatility: float | None) -> float:
    """Map raw realized volatility to a conservative [0, 100] score."""
    if volatility is None:
        return 0.0

    if volatility <= 0.005:
        return 25.0
    if volatility <= 0.01:
        return 50.0
    if volatility <= 0.02:
        return 75.0
    if volatility <= 0.03:
        return 55.0
    return 20.0


def build_feature_snapshot(
    payload: FeatureInput,
    ema_fast_period: int = 20,
    ema_slow_period: int = 50,
) -> FeatureSnapshotPayload:
    """Build deterministic feature snapshot output from bars and quotes."""
    if len(payload.bars) < max(ema_slow_period + 1, 30):
        raise ValueError("insufficient bars for deterministic feature calculation")

    highs, lows, closes = _to_bar_lists(payload.bars)

    ema_fast = calculate_ema(closes, ema_fast_period)
    ema_slow = calculate_ema(closes, ema_slow_period)
    rsi_result = calculate_rsi(closes, period=14)
    rsi_value = rsi_result.value if rsi_result is not None else None
    atr_value = calculate_atr(highs, lows, closes, period=14)

    adx_result = calculate_adx(highs, lows, closes, period=14)
    adx_value = adx_result.adx if adx_result is not None else None

    realized_vol_result = calculate_realized_volatility(closes, period=20)
    realized_vol = realized_vol_result.value if realized_vol_result is not None else None
    volatility_score = _normalize_volatility(realized_vol)

    trend_value = calculate_trend_score(closes, fast_period=20, slow_period=50, slope_lookback=5)
    trend_score = trend_value if trend_value is not None else 0.0

    momentum_value = calculate_momentum_score(closes, lookback=10)
    momentum_score = momentum_value if momentum_value is not None else 0.0

    liquidity_score = 0.0
    if payload.quotes:
        latest_quote = payload.quotes[-1]
        liquidity = assess_liquidity_from_quote(
            bid=latest_quote.bid,
            ask=latest_quote.ask,
            bid_size=latest_quote.bid_size,
            ask_size=latest_quote.ask_size,
        )
        if liquidity is not None:
            liquidity_score = liquidity.score

    regime = classify_regime(
        trend_score=trend_score,
        volatility=realized_vol if realized_vol is not None else 0.0,
        adx=adx_value,
    )

    market_quality_flag = assess_market_quality(
        liquidity_score=liquidity_score,
        volatility_score=volatility_score,
    )

    return FeatureSnapshotPayload(
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        rsi=rsi_value,
        atr=atr_value,
        adx=adx_value,
        volatility_score=volatility_score,
        liquidity_score=liquidity_score,
        trend_score=trend_score,
        momentum_score=momentum_score,
        regime_preclassification=regime,
        market_quality_flag=market_quality_flag,
    )
