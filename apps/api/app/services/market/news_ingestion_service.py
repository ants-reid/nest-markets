"""NewsIngestionService — ingest and persist news articles."""

from __future__ import annotations

from typing import Sequence

from app.clients.news.base import NewsAdapter, NewsRecord


class NewsIngestionService:
    """Coordinates news fetching from a provider."""

    def __init__(self, adapter: NewsAdapter) -> None:
        self._adapter = adapter

    async def ingest_news(
        self,
        symbols: Sequence[str] | None = None,
        *,
        limit: int = 50,
    ) -> list[NewsRecord]:
        """Fetch news from the provider.  Deduplication is caller's responsibility."""
        return list(await self._adapter.fetch_news(symbols, limit=limit))
