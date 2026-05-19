"""Market data service — ingest bars and quotes from an external client.

Upserts Bar rows using an INSERT ... ON CONFLICT DO UPDATE strategy so that
re-running ingestion for the same period does not create duplicate rows.
"""

from __future__ import annotations

from datetime import date, datetime, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.market_data.polygon_client import BarData, MarketDataClient
from app.db.models.asset import Asset
from app.db.models.bar import Bar


class AssetNotFoundError(Exception):
    """Raised when the requested ticker has no matching Asset row."""


class MarketDataService:
    """Orchestrate market data ingestion from an external client into the DB.

    Responsibilities:
      - Resolve ticker → asset_id.
      - Call the client to fetch bars.
      - Upsert rows into the bars table.
    """

    def __init__(self, client: MarketDataClient, session: Session) -> None:
        self._client = client
        self._session = session

    async def ingest_bars(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
        timeframe: str = "1d",
    ) -> int:
        """Fetch bars from client and upsert into the bars table.

        Returns the number of rows upserted (inserted or updated).
        """
        asset = self._get_asset(ticker)
        bars: list[BarData] = await self._client.get_bars(ticker, from_date, to_date, timeframe)
        if not bars:
            return 0

        rows: list[dict[str, Any]] = [
            {
                "asset_id": asset.id,
                "timeframe": bar.timeframe,
                "ts": datetime.fromtimestamp(bar.timestamp_ms / 1000, tz=UTC),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "source": "polygon",
            }
            for bar in bars
        ]

        stmt = (
            pg_insert(Bar)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_bars_asset_timeframe_ts",
                set_={
                    "open": pg_insert(Bar).excluded.open,
                    "high": pg_insert(Bar).excluded.high,
                    "low": pg_insert(Bar).excluded.low,
                    "close": pg_insert(Bar).excluded.close,
                    "volume": pg_insert(Bar).excluded.volume,
                    "source": pg_insert(Bar).excluded.source,
                },
            )
        )
        self._session.execute(stmt)
        return len(rows)

    def _get_asset(self, ticker: str) -> Asset:
        """Return the Asset row for the given ticker symbol or raise."""
        stmt = select(Asset).where(Asset.symbol == ticker.upper())
        asset = self._session.execute(stmt).scalar_one_or_none()
        if asset is None:
            raise AssetNotFoundError(
                f"No Asset row found for ticker '{ticker}'. "
                "Ensure the asset is registered before ingesting bars."
            )
        return asset
