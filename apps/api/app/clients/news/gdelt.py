"""GDELT events news adapter."""

from __future__ import annotations

from typing import Sequence

from app.clients.news.base import NewsAdapter, NewsRecord


class GDELTAdapter(NewsAdapter):
    """Fetches events from the GDELT Project open news feed."""

    _BASE_URL = "https://api.gdeltproject.org/api/v2"

    @property
    def provider_name(self) -> str:
        return "gdelt"

    async def fetch_news(
        self, symbols: Sequence[str] | None = None, *, limit: int = 50
    ) -> Sequence[NewsRecord]:
        raise NotImplementedError("GDELT fetch not yet implemented")

    async def health_check(self) -> bool:
        return False
