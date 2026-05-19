"""Polygon.io market data client.

Implements the ``MarketDataClient`` protocol and fetches OHLCV bars
from the Polygon REST API (v2 aggregates endpoint).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

import httpx

from app.config import get_settings

_POLYGON_BASE_URL = "https://api.polygon.io"


class PolygonAuthError(Exception):
    """Raised when Polygon returns HTTP 401 / 403."""


class PolygonAPIError(Exception):
    """Raised when Polygon returns an unexpected error response."""


@dataclass(frozen=True)
class BarData:
    """Single OHLCV bar returned by the market data client."""

    ticker: str
    timestamp_ms: int  # Unix epoch milliseconds (Polygon convention)
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str


@runtime_checkable
class MarketDataClient(Protocol):
    """Protocol for market data clients."""

    async def get_bars(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
        timeframe: str = "day",
    ) -> list[BarData]:
        """Fetch OHLCV bars for *ticker* between *from_date* and *to_date*."""
        ...


class PolygonClient:
    """Async Polygon REST client implementing ``MarketDataClient``.

    The API key is read from ``settings.polygon_api_key``.  An empty key
    disables the client — ``get_bars`` returns an empty list and logs a
    warning so the caller can degrade gracefully.
    """

    # Polygon multiplier/timespan pairs accepted by the aggregates endpoint
    _TIMEFRAME_MAP: dict[str, tuple[int, str]] = {
        "1m": (1, "minute"),
        "5m": (5, "minute"),
        "15m": (15, "minute"),
        "30m": (30, "minute"),
        "1h": (1, "hour"),
        "4h": (4, "hour"),
        "1d": (1, "day"),
        "day": (1, "day"),
        "week": (1, "week"),
    }

    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.polygon_api_key
        self._timeout = timeout

    async def get_bars(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
        timeframe: str = "day",
    ) -> list[BarData]:
        """Fetch OHLCV bars from Polygon /v2/aggs/ticker endpoint.

        Returns an empty list when ``polygon_api_key`` is not configured.
        Raises ``PolygonAuthError`` on HTTP 401/403.
        Raises ``PolygonAPIError`` on other non-200 responses.
        """
        if not self._api_key:
            return []

        multiplier, timespan = self._TIMEFRAME_MAP.get(timeframe, (1, "day"))
        url = (
            f"{_POLYGON_BASE_URL}/v2/aggs/ticker/{ticker.upper()}/range"
            f"/{multiplier}/{timespan}"
            f"/{from_date.isoformat()}/{to_date.isoformat()}"
        )
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
            "apiKey": self._api_key,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)

        if response.status_code in (401, 403):
            raise PolygonAuthError(
                f"Polygon authentication failed (HTTP {response.status_code})"
            )
        if response.status_code != 200:
            raise PolygonAPIError(
                f"Polygon API error (HTTP {response.status_code}): {response.text[:200]}"
            )

        payload = response.json()
        results = payload.get("results") or []

        return [
            BarData(
                ticker=ticker.upper(),
                timestamp_ms=r["t"],
                open=float(r["o"]),
                high=float(r["h"]),
                low=float(r["l"]),
                close=float(r["c"]),
                volume=float(r.get("v", 0)),
                timeframe=timeframe,
            )
            for r in results
        ]
