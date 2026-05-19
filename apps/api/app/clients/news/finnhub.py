"""Finnhub news adapter."""

from __future__ import annotations

from typing import Sequence

from app.clients.news.base import NewsAdapter, NewsRecord


class FinnhubNewsAdapter(NewsAdapter):
    """Fetches news from the Finnhub REST API."""

    _BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "finnhub"

    async def fetch_news(
        self, symbols: Sequence[str] | None = None, *, limit: int = 50
    ) -> Sequence[NewsRecord]:
        raise NotImplementedError("Finnhub fetch_news not yet implemented")

    async def health_check(self) -> bool:
        return False
