"""QA-112/QA-113: NewsClient and NewsIngestWorker tests."""
from __future__ import annotations

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.clients.news.news_client import (
    NewsClient,
    NewsItem,
    PlaceholderNewsClient,
    get_news_client,
)
from app.workers.news_ingest_worker import NewsIngestWorker


# ---------------------------------------------------------------------------
# QA-112: PlaceholderNewsClient
# ---------------------------------------------------------------------------


def test_placeholder_client_is_news_client():
    """PlaceholderNewsClient satisfies the NewsClient protocol."""
    client = PlaceholderNewsClient()
    assert isinstance(client, NewsClient)


def test_placeholder_client_returns_empty():
    """PlaceholderNewsClient.get_articles() always returns an empty list."""
    client = PlaceholderNewsClient()
    result = asyncio.run(client.get_articles("AAPL", limit=10))
    assert result == []


def test_get_news_client_returns_placeholder():
    """get_news_client() returns PlaceholderNewsClient when no key is set."""
    client = get_news_client()
    assert isinstance(client, PlaceholderNewsClient)


# ---------------------------------------------------------------------------
# QA-113: NewsIngestWorker
# ---------------------------------------------------------------------------


def _make_asset(symbol: str):
    a = MagicMock()
    a.symbol = symbol
    a.is_active = True
    return a


@pytest.mark.asyncio
async def test_news_ingest_worker_no_assets():
    """Worker returns a no-op message when no active assets exist."""
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    client = PlaceholderNewsClient()
    worker = NewsIngestWorker(client=client, session=session)
    result = await worker.execute(session)

    assert result.ingested == 0
    assert "skipped" in result.message or "no active" in result.message


@pytest.mark.asyncio
async def test_news_ingest_worker_placeholder_no_new_rows():
    """When placeholder client returns empty list, nothing is committed."""
    session = MagicMock()
    asset = _make_asset("AAPL")
    session.execute.return_value.scalars.return_value.all.return_value = [asset]

    client = PlaceholderNewsClient()
    worker = NewsIngestWorker(client=client, session=session)
    result = await worker.execute(session)

    assert result.ingested == 0
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_news_ingest_worker_ingests_new_article():
    """Worker persists a new article row and returns ingested=1."""

    session = MagicMock()
    asset = _make_asset("TSLA")
    session.execute.return_value.scalars.return_value.all.return_value = [asset]

    article = NewsItem(
        provider_article_id="art-001",
        published_at=datetime.now(timezone.utc),
        headline="TSLA reports record revenue",
        source_name="reuters",
    )

    mock_client = MagicMock()
    mock_client.get_articles = AsyncMock(return_value=[article])

    # No existing article found
    def _execute_side_effect(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = [asset]
        result.scalar_one_or_none.return_value = None
        return result

    session.execute.side_effect = _execute_side_effect

    worker = NewsIngestWorker(client=mock_client, session=session)
    result = await worker.execute(session)

    assert result.ingested == 1
    session.add.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_news_ingest_worker_skips_duplicate():
    """Worker skips an article that already exists (by provider_article_id)."""
    from app.db.models.news_article import NewsArticle

    session = MagicMock()
    asset = _make_asset("MSFT")
    session.execute.return_value.scalars.return_value.all.return_value = [asset]

    article = NewsItem(
        provider_article_id="art-dup",
        published_at=datetime.now(timezone.utc),
        headline="MSFT acquires something",
    )

    mock_client = MagicMock()
    mock_client.get_articles = AsyncMock(return_value=[article])

    existing_row = MagicMock(spec=NewsArticle)

    def _execute_side_effect(stmt):
        r = MagicMock()
        r.scalars.return_value.all.return_value = [asset]
        r.scalar_one_or_none.return_value = existing_row
        return r

    session.execute.side_effect = _execute_side_effect

    worker = NewsIngestWorker(client=mock_client, session=session)
    result = await worker.execute(session)

    assert result.skipped == 1
    assert result.ingested == 0
    session.add.assert_not_called()
