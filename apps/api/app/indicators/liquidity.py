"""Deterministic liquidity scoring helpers."""

from dataclasses import dataclass
from statistics import mean
from typing import Sequence


@dataclass(frozen=True)
class LiquidityAssessment:
    """Spread-derived liquidity assessment."""

    score: float
    spread_bps: float
    quality: str


@dataclass(frozen=True)
class SpreadQualityResult:
    """Bid/ask spread quality assessment."""

    spread_bps: float
    quality: str


def _quality_from_score(score: float) -> str:
    if score >= 80.0:
        return "excellent"
    if score >= 60.0:
        return "good"
    if score >= 40.0:
        return "fair"
    return "poor"


def _spread_quality_label(spread_bps: float) -> str:
    if spread_bps < 2.0:
        return "tight"
    if spread_bps < 8.0:
        return "normal"
    if spread_bps < 50.0:
        return "wide"
    return "extreme"


def calculate_spread_quality(
    bid_price: float,
    ask_price: float,
    mid_price: float,
) -> SpreadQualityResult:
    """Assess spread quality from bid/ask/mid prices.

    Raises:
        ValueError: If bid >= ask.
    """
    if bid_price >= ask_price:
        raise ValueError("bid_price must be less than ask_price")
    if mid_price <= 0.0:
        raise ValueError("mid_price must be positive")
    spread_bps = ((ask_price - bid_price) / mid_price) * 10_000.0
    return SpreadQualityResult(
        spread_bps=spread_bps,
        quality=_spread_quality_label(spread_bps),
    )


def assess_quote_liquidity(bid_size: float, ask_size: float) -> str:
    """Classify quote liquidity from bid and ask sizes.

    Returns:
        "high", "medium", or "low" based on minimum side size.
    """
    min_size = min(bid_size, ask_size)
    if min_size >= 500:
        return "high"
    if min_size >= 50:
        return "medium"
    return "low"


def calculate_liquidity_score(spreads_bps: Sequence[float]) -> float | None:
    """Calculate a simple liquidity score from spread values in basis points."""
    if not spreads_bps:
        return None

    average_spread = mean(float(value) for value in spreads_bps)

    if average_spread <= 2.0:
        return 90.0
    if average_spread <= 5.0:
        return 75.0
    if average_spread <= 10.0:
        return 55.0
    if average_spread <= 20.0:
        return 35.0
    return 15.0


def assess_liquidity_from_quote(
    bid: float,
    ask: float,
    bid_size: float | None = None,
    ask_size: float | None = None,
) -> LiquidityAssessment | None:
    """Assess liquidity from a single quote snapshot."""
    if bid <= 0.0 or ask <= 0.0 or ask <= bid:
        return None

    mid = (bid + ask) / 2.0
    spread_bps = ((ask - bid) / mid) * 10_000.0
    score = calculate_liquidity_score([spread_bps])
    if score is None:
        return None

    if bid_size is not None and ask_size is not None:
        min_size = max(min(bid_size, ask_size), 1.0)
        size_boost = min(min_size / 1_000.0, 1.0)
        score = min(100.0, score * (0.7 + (0.3 * size_boost)))

    return LiquidityAssessment(
        score=score,
        spread_bps=spread_bps,
        quality=_quality_from_score(score),
    )
