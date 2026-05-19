"""Phase 5 — ingestion service tests."""

from __future__ import annotations

import asyncio
from datetime import date


from app.clients.fundamentals.mock import MockFundamentalsAdapter
from app.clients.macro.mock import MockMacroAdapter
from app.clients.market_data.mock import MockMarketDataAdapter
from app.clients.news.mock import MockNewsAdapter
from app.services.market.fundamentals_ingestion_service import FundamentalsIngestionService
from app.services.market.instrument_registry_service import InstrumentRegistryService
from app.services.market.macro_ingestion_service import MacroIngestionService
from app.services.market.market_data_ingestion_service import MarketDataIngestionService
from app.services.market.news_ingestion_service import NewsIngestionService
from app.services.market.provider_dispatcher_service import ProviderDispatcherService


# ---------------------------------------------------------------------------
# MarketDataIngestionService
# ---------------------------------------------------------------------------

def test_market_data_ingest_bars():
    svc = MarketDataIngestionService(MockMarketDataAdapter())
    bars = asyncio.run(
        svc.ingest_bars("AAPL", "1D", date(2024, 1, 1), date(2024, 1, 3))
    )
    assert len(bars) >= 1
    assert bars[0].symbol == "AAPL"


# ---------------------------------------------------------------------------
# NewsIngestionService
# ---------------------------------------------------------------------------

def test_news_ingest():
    svc = NewsIngestionService(MockNewsAdapter())
    records = asyncio.run(svc.ingest_news(["AAPL"], limit=2))
    assert len(records) >= 1


# ---------------------------------------------------------------------------
# FundamentalsIngestionService
# ---------------------------------------------------------------------------

def test_fundamentals_ingest():
    svc = FundamentalsIngestionService(MockFundamentalsAdapter())
    record = asyncio.run(svc.ingest_fundamentals("TSLA"))
    assert record.symbol == "TSLA"


# ---------------------------------------------------------------------------
# MacroIngestionService
# ---------------------------------------------------------------------------

def test_macro_ingest():
    svc = MacroIngestionService(MockMacroAdapter())
    points = asyncio.run(
        svc.ingest_series("UNRATE", start=date(2023, 1, 1), end=date(2023, 3, 1))
    )
    assert len(points) >= 1


def test_macro_list_series():
    svc = MacroIngestionService(MockMacroAdapter())
    series = asyncio.run(svc.list_available_series())
    assert isinstance(series, list)


# ---------------------------------------------------------------------------
# InstrumentRegistryService
# ---------------------------------------------------------------------------

def test_instrument_registry_register_and_lookup():
    reg = InstrumentRegistryService()
    reg.register("AAPL", asset_class="equity", exchange="NASDAQ")
    info = reg.lookup("AAPL")
    assert info is not None
    assert info["exchange"] == "NASDAQ"


def test_instrument_registry_is_registered():
    reg = InstrumentRegistryService()
    assert not reg.is_registered("GOOG")
    reg.register("GOOG")
    assert reg.is_registered("GOOG")


def test_instrument_registry_all_symbols():
    reg = InstrumentRegistryService()
    reg.register("SPY")
    reg.register("QQQ")
    assert set(reg.all_symbols()) >= {"SPY", "QQQ"}


# ---------------------------------------------------------------------------
# ProviderDispatcherService
# ---------------------------------------------------------------------------

def test_dispatcher_returns_registered_providers():
    md = MockMarketDataAdapter()
    news = MockNewsAdapter()
    fundamentals = MockFundamentalsAdapter()
    macro = MockMacroAdapter()

    dispatcher = ProviderDispatcherService(
        market_data_providers=[md],
        news_providers=[news],
        fundamentals_providers=[fundamentals],
        macro_providers=[macro],
    )

    assert dispatcher.get_market_data_provider() is md
    assert dispatcher.get_news_provider() is news
    assert dispatcher.get_fundamentals_provider() is fundamentals
    assert dispatcher.get_macro_provider() is macro


def test_dispatcher_returns_none_when_empty():
    dispatcher = ProviderDispatcherService()
    assert dispatcher.get_market_data_provider() is None
    assert dispatcher.get_news_provider() is None
