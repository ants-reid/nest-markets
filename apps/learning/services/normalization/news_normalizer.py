"""NewsNormalizer — map provider-specific news fields to NewsRecord.

Each provider returns articles with different field names and date formats.
NewsNormalizer provides a uniform dict → NewsRecord conversion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dataclasses import dataclass


@dataclass(frozen=True)
class RawNewsArticle:
    """Provider-agnostic raw article container."""

    external_id: str
    headline: str
    source: str
    published_at: datetime
    summary: str | None = None
    url: str | None = None
    tickers: tuple[str, ...] = ()
    sentiment_score: float | None = None


class NewsNormalizer:
    """Convert raw provider dicts to a uniform RawNewsArticle."""

    def from_finnhub(self, raw: dict[str, Any]) -> RawNewsArticle:
        return RawNewsArticle(
            external_id=str(raw.get("id", "")),
            headline=raw.get("headline", ""),
            source=raw.get("source", "finnhub"),
            published_at=datetime.fromtimestamp(raw.get("datetime", 0), tz=timezone.utc),
            summary=raw.get("summary"),
            url=raw.get("url"),
            tickers=tuple(raw.get("related", "").split(",")) if raw.get("related") else (),
            sentiment_score=raw.get("sentiment"),
        )

    def from_alpaca(self, raw: dict[str, Any]) -> RawNewsArticle:
        return RawNewsArticle(
            external_id=str(raw.get("id", "")),
            headline=raw.get("headline", ""),
            source=raw.get("source", "alpaca"),
            published_at=datetime.fromisoformat(raw["created_at"]).replace(tzinfo=timezone.utc)
            if raw.get("created_at")
            else datetime.now(tz=timezone.utc),
            summary=raw.get("summary"),
            url=raw.get("url"),
            tickers=tuple(raw.get("symbols", [])),
        )
