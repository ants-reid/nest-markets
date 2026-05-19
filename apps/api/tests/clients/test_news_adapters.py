"""Phase 5 — news adapter tests."""

from __future__ import annotations

import asyncio

import pytest

from app.clients.news.alpaca_news import AlpacaNewsAdapter
from app.clients.news.base import NewsAdapter, NewsRecord
from app.clients.news.finnhub import FinnhubNewsAdapter
from app.clients.news.gdelt import GDELTAdapter
from app.clients.news.mock import MockNewsAdapter


def test_abstract_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        NewsAdapter()  # type: ignore[abstract]


@pytest.mark.parametrize("adapter_cls", [FinnhubNewsAdapter, AlpacaNewsAdapter, GDELTAdapter])
def test_stubs_raise_on_fetch_news(adapter_cls):
    adapter = adapter_cls()
    with pytest.raises(NotImplementedError):
        asyncio.run(adapter.fetch_news(["AAPL"]))


@pytest.mark.parametrize("adapter_cls", [FinnhubNewsAdapter, AlpacaNewsAdapter, GDELTAdapter])
def test_stubs_provider_names_are_strings(adapter_cls):
    assert isinstance(adapter_cls().provider_name, str)


def test_mock_provider_name():
    assert MockNewsAdapter().provider_name == "mock"


def test_mock_returns_news_records():
    records = asyncio.run(
        MockNewsAdapter().fetch_news(["TSLA"], limit=2)
    )
    assert len(records) >= 1
    assert all(isinstance(r, NewsRecord) for r in records)


def test_mock_health_check():
    ok = asyncio.run(MockNewsAdapter().health_check())
    assert ok is True
