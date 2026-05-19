"""Type definitions for indicator calculations."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BarData:
    """OHLCV bar data."""

    timestamp: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int


@dataclass
class QuoteData:
    """Bid/ask quote data."""

    timestamp: str
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float


@dataclass
class EMAResult:
    """Exponential Moving Average result."""

    value: Optional[float]
    period: int


@dataclass
class RSIResult:
    """Relative Strength Index result."""

    value: Optional[float]
    period: int


@dataclass
class ATRResult:
    """Average True Range result."""

    value: Optional[float]
    period: int


@dataclass
class ADXResult:
    """Average Directional Index result."""

    adx: Optional[float]
    di_plus: Optional[float]
    di_minus: Optional[float]
    period: int


@dataclass
class VolatilityResult:
    """Realized volatility result."""

    value: Optional[float]
    period: int
    annualized: Optional[float]


@dataclass
class SpreadQualityResult:
    """Bid/ask spread quality assessment."""

    spread_bps: float
    spread_pct: float
    quality: str  # tight, normal, wide, extreme


@dataclass
class TrendResult:
    """Trend analysis result."""

    direction: str  # up, down, neutral
    strength: float  # 0-1
    duration_bars: Optional[int]


@dataclass
class MomentumResult:
    """Momentum analysis result."""

    value: Optional[float]
    direction: str  # bullish, bearish, neutral
    strength: float  # 0-1


@dataclass
class RegimeResult:
    """Market regime classification result."""

    regime: str  # trending_up, trending_down, mean_reversion, ranging, high_vol, low_vol
    confidence: float  # 0-1
