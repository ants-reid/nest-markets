"""QA-106 — PolygonClient unit tests (mocked httpx)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.clients.market_data.polygon_client import (
    BarData,
    PolygonAuthError,
    PolygonAPIError,
    PolygonClient,
)

# ---------------------------------------------------------------------------
# Sample Polygon API response fixtures
# ---------------------------------------------------------------------------

_SAMPLE_POLYGON_BARS = {
    "status": "OK",
    "resultsCount": 2,
    "results": [
        {"t": 1713744000000, "o": 1.0800, "h": 1.0850, "l": 1.0780, "c": 1.0830, "v": 50000},
        {"t": 1713830400000, "o": 1.0830, "h": 1.0900, "l": 1.0810, "c": 1.0880, "v": 62000},
    ],
}

_FROM = date(2026, 4, 21)
_TO = date(2026, 4, 22)


def _make_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPolygonClient:
    """QA-106 — PolygonClient maps API responses to BarData objects."""

    @pytest.mark.asyncio
    async def test_get_bars_returns_bar_data_list(self):
        client = PolygonClient(api_key="test_key")
        mock_resp = _make_response(200, _SAMPLE_POLYGON_BARS)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_ctx

            bars = await client.get_bars("EURUSD", _FROM, _TO, timeframe="1d")

        assert len(bars) == 2
        assert all(isinstance(b, BarData) for b in bars)

    @pytest.mark.asyncio
    async def test_get_bars_maps_ohlcv_correctly(self):
        client = PolygonClient(api_key="test_key")
        mock_resp = _make_response(200, _SAMPLE_POLYGON_BARS)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_ctx

            bars = await client.get_bars("EURUSD", _FROM, _TO, timeframe="1d")

        b = bars[0]
        assert b.ticker == "EURUSD"
        assert b.open == pytest.approx(1.0800)
        assert b.high == pytest.approx(1.0850)
        assert b.low == pytest.approx(1.0780)
        assert b.close == pytest.approx(1.0830)
        assert b.volume == pytest.approx(50000)
        assert b.timeframe == "1d"

    @pytest.mark.asyncio
    async def test_get_bars_raises_polygon_auth_error_on_401(self):
        client = PolygonClient(api_key="bad_key")
        mock_resp = _make_response(401, {"status": "AUTH_ERROR"})

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_ctx

            with pytest.raises(PolygonAuthError):
                await client.get_bars("EURUSD", _FROM, _TO)

    @pytest.mark.asyncio
    async def test_get_bars_raises_polygon_api_error_on_500(self):
        client = PolygonClient(api_key="test_key")
        mock_resp = _make_response(500, {"status": "ERROR"})

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_ctx

            with pytest.raises(PolygonAPIError):
                await client.get_bars("EURUSD", _FROM, _TO)

    @pytest.mark.asyncio
    async def test_get_bars_returns_empty_list_when_no_api_key(self):
        client = PolygonClient(api_key="")
        bars = await client.get_bars("EURUSD", _FROM, _TO)
        assert bars == []

    @pytest.mark.asyncio
    async def test_get_bars_empty_results_key(self):
        client = PolygonClient(api_key="test_key")
        mock_resp = _make_response(200, {"status": "OK", "resultsCount": 0})

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_ctx.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_ctx

            bars = await client.get_bars("EURUSD", _FROM, _TO)

        assert bars == []
