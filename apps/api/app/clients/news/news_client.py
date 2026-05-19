"""API-C02 — NewsClient protocol and placeholder HTTP client.

The placeholder always returns an empty list so the worker is safe to
run even before a real news API key is configured.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.config import get_settings


@dataclass
class NewsItem:
    """Normalised representation of a single news article."""

    provider_article_id: str | None
    published_at: datetime
    headline: str
    summary: str | None = None
    body_text: str | None = None
    source_name: str | None = None
    url: str | None = None
    authors: list[str] = field(default_factory=list)
    tickers: list[str] = field(default_factory=list)
    sector_tags: list[str] = field(default_factory=list)
    raw: dict | None = None


@runtime_checkable
class NewsClient(Protocol):
    """Minimal contract for news data providers."""

    async def get_articles(
        self,
        ticker: str,
        *,
        from_date: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsItem]: ...


class PlaceholderNewsClient:
    """No-op client returned when no news API key is configured.

    Always returns an empty list so downstream workers degrade gracefully.
    """

    async def get_articles(
        self,
        ticker: str,
        *,
        from_date: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsItem]:
        return []


class PolygonNewsClient(PlaceholderNewsClient):
    """Polygon-backed scaffold.

    The concrete HTTP implementation is intentionally deferred; for RC-2 this
    preserves the provider-specific type while degrading safely to an empty
    result set when no news provider integration is configured.
    """


def get_news_client() -> NewsClient:
    """Return an appropriate NewsClient based on current settings.

    Extend this factory when real provider clients are added.
    """
    settings = get_settings()
    _ = settings
    return PolygonNewsClient()
