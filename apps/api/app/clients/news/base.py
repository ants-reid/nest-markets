"""Base interface for all news data adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class NewsRecord:
    """Normalized news article from any provider."""

    external_id: str
    headline: str
    source: str
    published_at: datetime
    summary: str | None = None
    url: str | None = None
    tickers: tuple[str, ...] = field(default_factory=tuple)
    sentiment_score: float | None = None


class NewsAdapter(ABC):
    """Abstract interface every news provider must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def fetch_news(
        self,
        symbols: Sequence[str] | None = None,
        *,
        limit: int = 50,
    ) -> Sequence[NewsRecord]:
        """Fetch recent news articles, optionally filtered by symbol."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider endpoint is reachable."""
