"""Mock market data adapter for testing."""

from __future__ import annotations

from datetime import date, datetime, timedelta, UTC
from typing import Sequence

from app.clients.market_data.base import BarRecord, MarketDataAdapter, QuoteRecord


class MockMarketDataAdapter(MarketDataAdapter):
    """Deterministic mock adapter for unit tests."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def fetch_bars(
        self, symbol: str, timeframe: str, start: date, end: date
    ) -> Sequence[BarRecord]:
        bars = []
        current = start
        price = 100.0
        while current <= end:
            bars.append(BarRecord(
                symbol=symbol,
                timestamp=current.isoformat(),
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price * 1.005,
                volume=10_000.0,
                timeframe=timeframe,
            ))
            current += timedelta(days=1)
            price *= 1.001
        return bars

    async def fetch_quote(self, symbol: str) -> QuoteRecord:
        return QuoteRecord(
            symbol=symbol,
            timestamp=datetime.now(UTC).isoformat(),
            bid=99.90,
            ask=100.10,
            bid_size=1000.0,
            ask_size=1000.0,
        )

    async def health_check(self) -> bool:
        return True
