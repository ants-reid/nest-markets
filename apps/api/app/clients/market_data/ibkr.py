"""IBKR market data adapter (HTTP Client Portal Gateway)."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from app.clients.market_data.base import BarRecord, MarketDataAdapter, QuoteRecord


class IBKRMarketDataAdapter(MarketDataAdapter):
    """Fetches market data via IB Client Portal Gateway REST API."""

    def __init__(self, gateway_url: str = "https://localhost:5000/v1/api") -> None:
        self._gateway_url = gateway_url

    @property
    def provider_name(self) -> str:
        return "ibkr"

    async def fetch_bars(
        self, symbol: str, timeframe: str, start: date, end: date
    ) -> Sequence[BarRecord]:
        # Phase 15: implement against /iserver/marketdata/history
        raise NotImplementedError("IBKR bar fetch not yet implemented — Phase 15")

    async def fetch_quote(self, symbol: str) -> QuoteRecord:
        # Phase 15: implement against /iserver/marketdata/snapshot
        raise NotImplementedError("IBKR quote fetch not yet implemented — Phase 15")

    async def health_check(self) -> bool:
        # Phase 15: implement tickle endpoint check
        return False
