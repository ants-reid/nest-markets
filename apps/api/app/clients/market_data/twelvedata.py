"""Twelve Data market data adapter."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from app.clients.market_data.base import BarRecord, MarketDataAdapter, QuoteRecord


class TwelveDataAdapter(MarketDataAdapter):
    """Fetches OHLCV bars from the Twelve Data REST API."""

    _BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "twelvedata"

    async def fetch_bars(
        self, symbol: str, timeframe: str, start: date, end: date
    ) -> Sequence[BarRecord]:
        # Phase 5 full implementation: POST /time_series
        raise NotImplementedError("TwelveData fetch_bars not yet implemented")

    async def fetch_quote(self, symbol: str) -> QuoteRecord:
        # Phase 5 full implementation: GET /quote
        raise NotImplementedError("TwelveData fetch_quote not yet implemented")

    async def health_check(self) -> bool:
        return False
