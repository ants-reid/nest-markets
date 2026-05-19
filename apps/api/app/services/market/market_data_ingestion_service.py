"""MarketDataIngestionService — ingest and persist OHLCV bars."""

from __future__ import annotations

from datetime import date

from app.clients.market_data.base import BarRecord, MarketDataAdapter


class MarketDataIngestionService:
    """Coordinates bar fetching from a provider and persistence to the DB."""

    def __init__(self, adapter: MarketDataAdapter) -> None:
        self._adapter = adapter

    async def ingest_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[BarRecord]:
        """Fetch bars from the provider.  Persistence is caller's responsibility."""
        return list(await self._adapter.fetch_bars(symbol, timeframe, start, end))
