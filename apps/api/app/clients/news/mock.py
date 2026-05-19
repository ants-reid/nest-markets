"""Mock news adapter for testing."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Sequence

from app.clients.news.base import NewsAdapter, NewsRecord


class MockNewsAdapter(NewsAdapter):
    """Deterministic mock news adapter for unit tests."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def fetch_news(
        self, symbols: Sequence[str] | None = None, *, limit: int = 50
    ) -> Sequence[NewsRecord]:
        symbol_list = list(symbols) if symbols else ["AAPL"]
        return [
            NewsRecord(
                external_id=f"mock-{i}",
                headline=f"Mock headline {i} for {symbol_list[0] if symbol_list else 'market'}",
                source="mock_provider",
                published_at=datetime.now(UTC),
                summary="Mock summary.",
                tickers=tuple(symbol_list[:1]),
            )
            for i in range(min(3, limit))
        ]

    async def health_check(self) -> bool:
        return True
