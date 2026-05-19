"""Spread quality assessment.

Pure deterministic function for spread analysis with no side effects.
"""

from app.indicators.types import SpreadQualityResult


def calculate_spread_quality(
    bid_price: float, ask_price: float, mid_price: float
) -> SpreadQualityResult:
    """Calculate bid/ask spread quality.

    Args:
        bid_price: Current bid price.
        ask_price: Current ask price.
        mid_price: Mid price for reference.

    Returns:
        SpreadQualityResult with spread metrics and quality assessment.
    """
    if bid_price <= 0 or ask_price <= 0 or mid_price <= 0:
        raise ValueError("Prices must be positive")

    if bid_price >= ask_price:
        raise ValueError("Bid price must be less than ask price")

    spread = ask_price - bid_price
    spread_pct = (spread / mid_price) * 100
    spread_bps = spread_pct * 100  # Convert to basis points

    # Quality assessment thresholds
    if spread_bps <= 1.0:
        quality = "tight"
    elif spread_bps <= 5.0:
        quality = "normal"
    elif spread_bps <= 25.0:
        quality = "wide"
    else:
        quality = "extreme"

    return SpreadQualityResult(
        spread_bps=spread_bps, spread_pct=spread_pct, quality=quality
    )


def assess_quote_liquidity(bid_size: float, ask_size: float) -> str:
    """Assess quote liquidity quality based on sizes.

    Args:
        bid_size: Bid size (quantity).
        ask_size: Ask size (quantity).

    Returns:
        Liquidity assessment: "high", "medium", "low".
    """
    min_size = min(bid_size, ask_size)

    if min_size >= 1000:
        return "high"
    elif min_size >= 100:
        return "medium"
    else:
        return "low"
