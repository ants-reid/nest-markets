"""Alpaca news adapter."""

from __future__ import annotations

from typing import Sequence

from app.clients.news.base import NewsAdapter, NewsRecord


class AlpacaNewsAdapter(NewsAdapter):
    """Fetches news from the Alpaca Markets News API."""

    _BASE_URL = "https://data.alpaca.markets/v1beta1/news"

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self._api_key = api_key
        self._api_secret = api_secret

    @property
    def provider_name(self) -> str:
        return "alpaca_news"

    async def fetch_news(
        self, symbols: Sequence[str] | None = None, *, limit: int = 50
    ) -> Sequence[NewsRecord]:
        raise NotImplementedError("Alpaca news fetch not yet implemented")

    async def health_check(self) -> bool:
        return False
