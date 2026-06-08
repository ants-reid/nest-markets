"""HistoricalImportWorker — scheduled historical bar import for active assets.

This worker is opt-in via settings and designed for unattended paper-mode
operations so the model inputs continue to fill while the system trades.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import get_settings
from app.db.models.asset import Asset
from app.db.session import SessionLocal
from app.services.historical_import_service import HistoricalImportService
from app.workers.async_bridge import run_async
from app.workers.base_worker import BaseWorker

_logger = logging.getLogger(__name__)


class HistoricalImportWorker(BaseWorker):
    """Run a batch historical import for active assets and configured timeframes."""

    worker_name = "historical_import"

    def execute(self) -> str:
        settings = get_settings()
        if not settings.auto_history_import_enabled:
            return "historical_import: skipped (AUTO_HISTORY_IMPORT_ENABLED=false)"

        session = SessionLocal()
        try:
            assets = [
                symbol
                for symbol in session.execute(
                    select(Asset.symbol).where(Asset.is_active.is_(True))
                ).scalars().all()
                if symbol
            ]
            if not assets:
                return "historical_import: skipped (no active assets)"

            provider = (settings.auto_history_import_provider or "yfinance").strip().lower()
            timeframes = [
                timeframe.strip().lower()
                for timeframe in (settings.auto_history_import_timeframes or "1d").split(",")
                if timeframe and timeframe.strip()
            ]
            if not timeframes:
                timeframes = ["1d"]

            requested_years = max(1, min(int(settings.auto_history_import_requested_years), 20))
            service = HistoricalImportService(session)
            result = run_async(
                lambda: service.run_import(
                    assets=assets,
                    timeframes=timeframes,
                    providers=[provider],
                    requested_years=requested_years,
                    dry_run=False,
                )
            )
            session.commit()

            failed = sum(1 for item in result.results if item.status == "failed")
            skipped = sum(1 for item in result.results if item.status == "skipped")
            return (
                "historical_import: "
                f"status={result.status} "
                f"assets={len(assets)} "
                f"timeframes={','.join(timeframes)} "
                f"provider={provider} "
                f"candles={result.total_candles_imported} "
                f"failed={failed} skipped={skipped}"
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            _logger.error("historical_import fatal error: %s", exc)
            return f"historical_import: fatal error - {exc}"
        finally:
            session.close()
