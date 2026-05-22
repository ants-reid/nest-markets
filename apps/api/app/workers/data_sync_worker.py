"""DataSyncWorker — fetches market data bars via YFinanceClient (default) or PolygonClient."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.market_data.polygon_client import PolygonClient
from app.clients.market_data.yfinance_client import YFinanceClient
from app.config import get_settings
from app.db.models.asset import Asset
from app.db.session import SessionLocal
from app.services.market_data_service import AssetNotFoundError, MarketDataService
from app.workers.async_bridge import run_async
from app.workers.base_worker import BaseWorker

_logger = logging.getLogger(__name__)


class DataSyncWorker(BaseWorker):
    """Synchronise market data for all active assets on a scheduled cadence.

    Uses ``YFinanceClient`` by default (no API key required).
    Falls back to ``PolygonClient`` if ``polygon_api_key`` is configured.
    Errors per-asset are caught and logged; the worker continues with
    remaining assets and reports the final tally.
    """

    worker_name = "data_sync"
    lookback_days: int = 90  # fetch up to 90 days of daily bars on first run

    def __init__(
        self,
        client: PolygonClient | YFinanceClient | None = None,
        session: Session | None = None,
    ) -> None:
        settings = get_settings()
        if client is not None:
            self._client = client
        elif settings.polygon_api_key:
            self._client = PolygonClient(api_key=settings.polygon_api_key)
        else:
            self._client = YFinanceClient()
        self._session = session

    def execute(self) -> str:

        session = self._session or SessionLocal()
        close_session = self._session is None
        total = 0
        errors: list[str] = []

        try:
            service = MarketDataService(self._client, session)
            assets = session.execute(select(Asset)).scalars().all()
            to_date = date.today()
            from_date = to_date - timedelta(days=self.lookback_days)

            for asset in assets:
                try:
                    count = run_async(
                        lambda asset=asset: service.ingest_bars(
                            asset.symbol,
                            from_date,
                            to_date,
                            timeframe="1d",
                        )
                    )
                    total += count
                except AssetNotFoundError:
                    pass  # shouldn't happen since we loaded from DB
                except Exception as exc:
                    msg = f"{asset.symbol}: {exc}"
                    errors.append(msg)
                    _logger.warning("data_sync error for %s: %s", asset.symbol, exc)

            session.commit()
        except Exception as exc:
            session.rollback()
            _logger.error("data_sync fatal error: %s", exc)
            return f"data_sync: fatal error — {exc}"
        finally:
            if close_session:
                session.close()

        if errors:
            return f"data_sync: {total} rows upserted; {len(errors)} asset errors: {'; '.join(errors)}"
        return f"data_sync: {total} rows upserted across {len(list(assets))} assets"
