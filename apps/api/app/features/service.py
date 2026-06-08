"""Feature calculation service.

Orchestrates indicator calculations and produces structured feature snapshots.
No database writes - returns data ready for persistence.
"""

from datetime import datetime
from typing import Optional

from app.indicators import (
    assess_market_quality,
    calculate_adx,
    calculate_atr,
    calculate_ema,
    calculate_momentum_score,
    calculate_parkinson_volatility,
    calculate_roc,
    calculate_rsi,
    calculate_spread_quality,
    calculate_trend_score,
    classify_regime,
)


def calculate_features(
    bars: list[dict],
    quotes: Optional[list[dict]] = None,
    asset_id: str = "",
    timestamp: Optional[datetime] = None,
) -> dict:
    """Calculate all features for a bar snapshot.

    Args:
        bars: List of bar dicts with 'high', 'low', 'close', 'volume' keys.
        quotes: Optional list of quote dicts with bid/ask info.
        asset_id: Asset ID for the snapshot.
        timestamp: Timestamp for the snapshot (defaults to now).

    Returns:
        Dictionary with all calculated features ready for FeatureSnapshot persistence.

    Raises:
        ValueError: If bars list is empty or invalid.
    """
    if not bars or len(bars) < 20:
        raise ValueError("Need at least 20 bars for feature calculation")

    if timestamp is None:
        timestamp = datetime.utcnow()

    # Extract close prices for calculations
    closes = [bar["close"] for bar in bars]

    # Calculate moving averages
    calculate_ema(closes, 20)
    calculate_ema(closes, 50)
    calculate_ema(closes, 200)
    sma_20_val = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    sma_50_val = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    sma_200_val = sum(closes[-200:]) / 200 if len(closes) >= 200 else None

    # Calculate momentum indicators
    rsi_14 = calculate_rsi(closes, 14)
    rsi_14_value = rsi_14.value if rsi_14 is not None else None
    atr_14 = calculate_atr(bars, 14)
    atr_14_value = atr_14.value if hasattr(atr_14, "value") else atr_14
    adx_14 = calculate_adx(bars, 14)

    # Calculate volatility
    volatility = calculate_parkinson_volatility(bars, 20)
    volatility_value = volatility.value if hasattr(volatility, "value") else volatility

    # Calculate trend
    trend = calculate_trend_score(
        sma_20_val or closes[-1],
        sma_50_val or closes[-1],
        sma_200_val or closes[-1],
        closes[-1],
        bars_up=_count_up_bars(closes, 20),
        bars_down=_count_down_bars(closes, 20),
    )

    # Calculate momentum
    roc_12 = calculate_roc(closes, 12)
    calculate_momentum_score(
        rsi_14_value or 50,
        roc_12.value or 0,
        (adx_14.adx if adx_14 is not None else 20),
    )

    # Calculate spread quality if quotes available
    spread_quality = None
    market_quality = None
    if quotes and len(quotes) > 0:
        latest_quote = quotes[-1]
        mid_price = (latest_quote["bid_price"] + latest_quote["ask_price"]) / 2
        spread_quality = calculate_spread_quality(
            latest_quote["bid_price"], latest_quote["ask_price"], mid_price
        )

    # Calculate regime
    volume_ratio = _calculate_volume_ratio(bars, 20)
    classify_regime(
        (adx_14.adx if adx_14 is not None else 20),
        rsi_14_value or 50,
        volatility_value or 0.01,
        trend.direction,
        trend.strength,
    )

    # Market quality assessment
    if spread_quality:
        market_quality = assess_market_quality(
            spread_quality.spread_bps,
            volatility_value or 0.01,
            volume_ratio,
        )

    features = {
        "asset_id": asset_id,
        "timestamp": timestamp,
        # SMAs
        "sma_20": sma_20_val,
        "sma_50": sma_50_val,
        "sma_200": sma_200_val,
        # Momentum
        "rsi_14": rsi_14_value,
        "atr_14": atr_14_value,
        "bb_upper": _calculate_bb_upper(sma_20_val, atr_14_value) if sma_20_val and atr_14_value else None,
        "bb_middle": sma_20_val,
        "bb_lower": _calculate_bb_lower(sma_20_val, atr_14_value) if sma_20_val and atr_14_value else None,
        # Volatility
        "volatility": volatility_value,
        # Trend
        "trend_direction": trend.direction,
        "trend_strength": trend.strength,
        # Market quality
        "market_quality": market_quality,
        "volume_ratio": volume_ratio,
        # Spread (if available)
        "spread_bps": spread_quality.spread_bps if spread_quality else None,
    }

    return features


def _count_up_bars(closes: list[float], period: int) -> int:
    """Count consecutive up bars from the end.

    Args:
        closes: List of close prices.
        period: Maximum period to check.

    Returns:
        Number of consecutive up bars.
    """
    count = 0
    for i in range(len(closes) - 1, max(len(closes) - period - 1, 0), -1):
        if i > 0 and closes[i] > closes[i - 1]:
            count += 1
        else:
            break
    return count


def _count_down_bars(closes: list[float], period: int) -> int:
    """Count consecutive down bars from the end.

    Args:
        closes: List of close prices.
        period: Maximum period to check.

    Returns:
        Number of consecutive down bars.
    """
    count = 0
    for i in range(len(closes) - 1, max(len(closes) - period - 1, 0), -1):
        if i > 0 and closes[i] < closes[i - 1]:
            count += 1
        else:
            break
    return count


def _calculate_volume_ratio(bars: list[dict], period: int) -> float:
    """Calculate volume ratio (current vs average).

    Args:
        bars: List of bars with volume.
        period: Period for average.

    Returns:
        Ratio of current volume to average.
    """
    if not bars or len(bars) < period:
        return 1.0

    current_volume = bars[-1]["volume"]
    avg_volume = sum(bar["volume"] for bar in bars[-period:]) / period

    if avg_volume == 0:
        return 1.0

    return current_volume / avg_volume


def _calculate_bb_upper(sma: Optional[float], atr: Optional[float]) -> Optional[float]:
    """Calculate Bollinger Bands upper band.

    Args:
        sma: Simple moving average (middle band).
        atr: Average true range for volatility adjustment.

    Returns:
        Upper band or None if insufficient data.
    """
    if sma is None or atr is None:
        return None
    return sma + (atr * 2)


def _calculate_bb_lower(sma: Optional[float], atr: Optional[float]) -> Optional[float]:
    """Calculate Bollinger Bands lower band.

    Args:
        sma: Simple moving average (middle band).
        atr: Average true range for volatility adjustment.

    Returns:
        Lower band or None if insufficient data.
    """
    if sma is None or atr is None:
        return None
    return sma - (atr * 2)
