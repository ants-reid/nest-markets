"""Phase 5 — market data adapter tests."""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from app.clients.market_data.base import BarRecord, MarketDataAdapter, QuoteRecord
from app.clients.market_data.ibkr import IBKRMarketDataAdapter
from app.clients.market_data.mock import MockMarketDataAdapter
from app.clients.market_data.tiingo import TiingoAdapter
from app.clients.market_data.twelvedata import TwelveDataAdapter


# ---------------------------------------------------------------------------
# Abstract contract
# ---------------------------------------------------------------------------

def test_abstract_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        MarketDataAdapter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Stub providers raise NotImplementedError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("adapter_cls", [IBKRMarketDataAdapter, TiingoAdapter, TwelveDataAdapter])
def test_stubs_raise_on_fetch_bars(adapter_cls):
    adapter = adapter_cls()
    with pytest.raises(NotImplementedError):
        asyncio.run(
            adapter.fetch_bars("AAPL", "1D", date(2024, 1, 1), date(2024, 1, 31))
        )


@pytest.mark.parametrize("adapter_cls", [IBKRMarketDataAdapter, TiingoAdapter, TwelveDataAdapter])
def test_stubs_raise_on_fetch_quote(adapter_cls):
    adapter = adapter_cls()
    with pytest.raises(NotImplementedError):
        asyncio.run(adapter.fetch_quote("AAPL"))


@pytest.mark.parametrize("adapter_cls", [IBKRMarketDataAdapter, TiingoAdapter, TwelveDataAdapter])
def test_stubs_provider_names_are_strings(adapter_cls):
    assert isinstance(adapter_cls().provider_name, str)


# ---------------------------------------------------------------------------
# Mock adapter returns real data
# ---------------------------------------------------------------------------

def test_mock_provider_name():
    assert MockMarketDataAdapter().provider_name == "mock"


def test_mock_fetch_bars_returns_bar_records():
    adapter = MockMarketDataAdapter()
    bars = asyncio.run(
        adapter.fetch_bars("SPY", "1D", date(2024, 1, 1), date(2024, 1, 5))
    )
    assert len(bars) >= 1
    assert all(isinstance(b, BarRecord) for b in bars)
    assert all(b.symbol == "SPY" for b in bars)


def test_mock_fetch_quote_returns_quote_record():
    adapter = MockMarketDataAdapter()
    quote = asyncio.run(adapter.fetch_quote("SPY"))
    assert isinstance(quote, QuoteRecord)
    assert quote.symbol == "SPY"
    assert quote.bid < quote.ask


def test_mock_health_check_returns_true():
    adapter = MockMarketDataAdapter()
    ok = asyncio.run(adapter.health_check())
    assert ok is True
