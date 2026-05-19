"""SignalSweepWorker — iterates the active asset universe and generates signals.

For each active asset the worker:
1. Fetches recent price bars from Polygon (1-day timeframe).
2. Builds a minimal feature snapshot from those bars.
3. Calls SignalService to generate a structured signal.
4. Persists the signal via PersistenceSignalService.

The worker is designed to be fully test-injectable: pass ``client`` and
``session`` in the constructor to avoid real I/O during tests.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.llm.router import LLMProviderRouter
from app.clients.market_data.polygon_client import PolygonClient
from app.config import get_settings
from app.db.models.asset import Asset
from app.db.session import SessionLocal
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.signal_service import SignalInput, SignalService
from app.workers.base_worker import BaseWorker

_logger = logging.getLogger(__name__)

# Number of daily bars to look back when building the feature snapshot
_LOOKBACK_DAYS = 5


def _build_feature_snapshot(bars: list) -> dict:
    """Build a minimal feature snapshot dict from recent OHLCV bars."""
    if not bars:
        return {"bar_count": 0}
    latest = bars[-1]
    closes = [b.close for b in bars if b.close is not None]
    high = max((b.high for b in bars if b.high is not None), default=0.0)
    low = min((b.low for b in bars if b.low is not None), default=0.0)
    avg_volume = sum(b.volume for b in bars if b.volume is not None) / max(len(bars), 1)
    return {
        "bar_count": len(bars),
        "open": bars[0].open,
        "high": high,
        "low": low,
        "close": latest.close,
        "volume": latest.volume,
        "avg_volume": round(avg_volume, 2),
        "price_change_pct": round((closes[-1] - closes[0]) / closes[0] * 100, 4) if len(closes) >= 2 else 0.0,
        "bars": [{"o": b.open, "h": b.high, "l": b.low, "c": b.close, "v": b.volume} for b in bars],
    }


class SignalSweepWorker(BaseWorker):
    """Sweep all active assets, generate signals, and persist results."""

    worker_name = "signal_sweep"

    def __init__(
        self,
        client: PolygonClient | None = None,
        session: Session | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client or PolygonClient(api_key=settings.polygon_api_key)
        self._session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _sweep(self, session: Session) -> tuple[int, int, list[str]]:
        """Run the sweep coroutine; returns (processed, persisted, errors)."""
        assets = session.execute(
            select(Asset).where(Asset.is_active.is_(True))
        ).scalars().all()

        llm_router = LLMProviderRouter(get_settings())
        signal_service = SignalService(router=llm_router, session=session)
        persistence = PersistenceSignalService(session)

        to_date = date.today()
        from_date = to_date - timedelta(days=_LOOKBACK_DAYS)

        processed = 0
        persisted = 0
        errors: list[str] = []

        for asset in assets:
            try:
                bars = await self._client.get_bars(
                    ticker=asset.symbol,
                    from_date=from_date,
                    to_date=to_date,
                    timeframe="1d",
                )
                if not bars:
                    _logger.debug("signal_sweep: no bars for %s, skipping", asset.symbol)
                    processed += 1
                    continue

                latest_price = float(bars[-1].close or 0.0)
                feature_snapshot = _build_feature_snapshot(bars)

                signal_input = SignalInput(
                    feature_snapshot=feature_snapshot,
                    catalyst_context={"source": "sweep", "symbol": asset.symbol},
                    asset=asset.symbol,
                    timeframe="1d",
                    latest_price=latest_price,
                )

                signal_output = await signal_service.generate_signal(signal_input)
                persistence.persist_signal(signal_output)
                persisted += 1
                processed += 1

            except Exception as exc:
                errors.append(f"{asset.symbol}: {exc}")
                _logger.warning("signal_sweep error for %s: %s", asset.symbol, exc)
                processed += 1

        return processed, persisted, errors

    # ------------------------------------------------------------------
    # BaseWorker contract
    # ------------------------------------------------------------------

    def execute(self) -> str:
        session = self._session or SessionLocal()
        close_session = self._session is None

        try:
            processed, persisted, errors = asyncio.run(self._sweep(session))
            session.commit()
        except Exception as exc:
            session.rollback()
            _logger.error("signal_sweep fatal error: %s", exc)
            return f"signal_sweep: fatal error — {exc}"
        finally:
            if close_session:
                session.close()

        suffix = f"; {len(errors)} errors: {'; '.join(errors)}" if errors else ""
        return f"signal_sweep: {processed} assets processed, {persisted} signals generated{suffix}"
