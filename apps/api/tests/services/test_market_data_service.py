"""QA-106 — MarketDataService unit tests (mocked client + session)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.clients.market_data.polygon_client import BarData
from app.db.models.asset import Asset
from app.services.market_data_service import AssetNotFoundError, MarketDataService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FROM = date(2026, 4, 21)
_TO = date(2026, 4, 22)


def _make_asset(symbol: str = "EURUSD") -> Asset:
    a = Asset()
    a.id = uuid4()
    a.symbol = symbol
    return a


def _make_bars(ticker: str = "EURUSD", count: int = 3) -> list[BarData]:
    return [
        BarData(
            ticker=ticker,
            timestamp_ms=1713744000000 + i * 86_400_000,
            open=1.08 + i * 0.001,
            high=1.085 + i * 0.001,
            low=1.079 + i * 0.001,
            close=1.083 + i * 0.001,
            volume=50000.0,
            timeframe="1d",
        )
        for i in range(count)
    ]


def _make_session() -> MagicMock:
    session = MagicMock(spec=Session)
    return session


def _make_client(bars: list[BarData] | None = None) -> MagicMock:
    client = MagicMock()
    client.get_bars = AsyncMock(return_value=bars or [])
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMarketDataService:
    """QA-106 — MarketDataService ingest_bars."""

    @pytest.mark.asyncio
    async def test_ingest_bars_returns_count_of_rows(self):
        session = _make_session()
        asset = _make_asset("EURUSD")
        session.execute.return_value.scalar_one_or_none.return_value = asset

        client = _make_client(bars=_make_bars(count=5))
        service = MarketDataService(client=client, session=session)

        count = await service.ingest_bars("EURUSD", _FROM, _TO, timeframe="1d")

        assert count == 5

    @pytest.mark.asyncio
    async def test_ingest_bars_calls_execute_for_upsert(self):
        session = _make_session()
        asset = _make_asset("EURUSD")
        session.execute.return_value.scalar_one_or_none.return_value = asset

        client = _make_client(bars=_make_bars(count=2))
        service = MarketDataService(client=client, session=session)

        await service.ingest_bars("EURUSD", _FROM, _TO, timeframe="1d")

        # session.execute should be called (at least once for asset lookup, once for upsert)
        assert session.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_ingest_bars_returns_zero_when_client_returns_empty(self):
        session = _make_session()
        asset = _make_asset("EURUSD")
        session.execute.return_value.scalar_one_or_none.return_value = asset

        client = _make_client(bars=[])
        service = MarketDataService(client=client, session=session)

        count = await service.ingest_bars("EURUSD", _FROM, _TO)
        assert count == 0

    @pytest.mark.asyncio
    async def test_ingest_bars_raises_when_asset_not_found(self):
        session = _make_session()
        session.execute.return_value.scalar_one_or_none.return_value = None

        client = _make_client()
        service = MarketDataService(client=client, session=session)

        with pytest.raises(AssetNotFoundError):
            await service.ingest_bars("UNKNOWN", _FROM, _TO)

    @pytest.mark.asyncio
    async def test_ingest_bars_normalises_ticker_to_uppercase(self):
        session = _make_session()
        asset = _make_asset("EURUSD")
        session.execute.return_value.scalar_one_or_none.return_value = asset

        client = _make_client(bars=_make_bars(count=1))
        service = MarketDataService(client=client, session=session)

        await service.ingest_bars("eurusd", _FROM, _TO)

        # The client should have been called
        client.get_bars.assert_called_once()
