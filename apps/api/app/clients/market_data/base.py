"""Base interface for all market data adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class BarRecord:
    """Normalized OHLCV bar."""

    symbol: str
    timestamp: str  # ISO-8601
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float | None = None
    timeframe: str = "1D"


@dataclass(frozen=True)
class QuoteRecord:
    """Normalized bid/ask quote."""

    symbol: str
    timestamp: str  # ISO-8601
    bid: float | None
    ask: float | None
    bid_size: float | None = None
    ask_size: float | None = None


class MarketDataAdapter(ABC):
    """Abstract interface every market data provider must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> Sequence[BarRecord]:
        """Fetch historical OHLCV bars for a symbol."""

    @abstractmethod
    async def fetch_quote(self, symbol: str) -> QuoteRecord:
        """Fetch the latest bid/ask quote for a symbol."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider endpoint is reachable."""
