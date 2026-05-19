"""Tests for MH-NEWS-01 — Perplexity / Sonar news adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.clients.news.perplexity import (
    PerplexityCitation,
    PerplexityNewsAdapter,
    PerplexityNewsRecord,
)


def test_provider_name():
    a = PerplexityNewsAdapter(api_key="k")
    assert a.provider_name == "perplexity_sonar"


@pytest.mark.asyncio
async def test_fetch_news_requires_api_key():
    a = PerplexityNewsAdapter(api_key="")
    with pytest.raises(RuntimeError, match="api_key is required"):
        await a.fetch_news(["AAPL"])


@pytest.mark.asyncio
async def test_fetch_news_requires_http_client():
    a = PerplexityNewsAdapter(api_key="k", http_client=None)
    with pytest.raises(RuntimeError, match="no http_client injected"):
        await a.fetch_news(["AAPL"])


@pytest.mark.asyncio
async def test_health_check_false_without_credentials():
    assert await PerplexityNewsAdapter(api_key="").health_check() is False
    assert await PerplexityNewsAdapter(api_key="k", http_client=None).health_check() is False


@pytest.mark.asyncio
async def test_health_check_true_when_configured():
    class _StubClient:
        async def post(self, *a, **kw):  # pragma: no cover
            return {}

    a = PerplexityNewsAdapter(api_key="k", http_client=_StubClient())
    assert await a.health_check() is True


@pytest.mark.asyncio
async def test_fetch_news_parses_response():
    captured: dict = {}

    class _StubClient:
        async def post(self, url, *, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return {
                "items": [
                    {
                        "external_id": "abc",
                        "headline": "Apple beats",
                        "summary": "Q3 results.",
                        "source": "reuters.com",
                        "url": "https://r.example/1",
                        "published_at": "2026-05-02T12:00:00Z",
                        "tickers": ["AAPL"],
                    }
                ],
                "citations": [
                    {"url": "https://r.example/1", "title": "Source"},
                ],
            }

    a = PerplexityNewsAdapter(api_key="key123", http_client=_StubClient())
    out = await a.fetch_news(["AAPL"])
    assert len(out) == 1
    rec = out[0]
    assert isinstance(rec, PerplexityNewsRecord)
    assert rec.headline == "Apple beats"
    assert rec.tickers == ("AAPL",)
    assert rec.citations and isinstance(rec.citations[0], PerplexityCitation)
    assert rec.citations[0].url == "https://r.example/1"
    assert rec.published_at == datetime(2026, 5, 2, 12, 0, tzinfo=UTC)
    # Auth + payload shape
    assert captured["headers"]["Authorization"] == "Bearer key123"
    assert captured["json"]["return_citations"] is True
    assert captured["json"]["model"] == "sonar-small-online"
