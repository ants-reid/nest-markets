"""FundamentalsIngestionService — ingest and persist company fundamentals."""

from __future__ import annotations

from app.clients.fundamentals.base import FundamentalsAdapter, FundamentalsRecord


class FundamentalsIngestionService:
    """Coordinates fundamentals fetching from a provider."""

    def __init__(self, adapter: FundamentalsAdapter) -> None:
        self._adapter = adapter

    async def ingest_fundamentals(self, symbol: str) -> FundamentalsRecord:
        """Fetch fundamentals for a symbol."""
        return await self._adapter.fetch_fundamentals(symbol)
