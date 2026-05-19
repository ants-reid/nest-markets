"""Tiingo market data adapter."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from app.clients.market_data.base import BarRecord, MarketDataAdapter, QuoteRecord


class TiingoAdapter(MarketDataAdapter):
    """Fetches OHLCV bars from the Tiingo REST API."""

    _BASE_URL = "https://api.tiingo.com"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "tiingo"

    async def fetch_bars(
        self, symbol: str, timeframe: str, start: date, end: date
    ) -> Sequence[BarRecord]:
        raise NotImplementedError("Tiingo fetch_bars not yet implemented")

    async def fetch_quote(self, symbol: str) -> QuoteRecord:
        raise NotImplementedError("Tiingo fetch_quote not yet implemented")

    async def health_check(self) -> bool:
        return False
