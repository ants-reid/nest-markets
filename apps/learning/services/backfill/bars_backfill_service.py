"""BarsBackfillService — coordinate historical bar ingestion."""

from __future__ import annotations

from datetime import date
from typing import Sequence


class BarsBackfillService:
    """Fetches historical OHLCV bars and persists them idempotently.

    In Phase 6 this is a coordination stub.  Full persistence wiring
    (adapter selection via ProviderDispatcherService, session factory,
    upsert into price_bars table) is done in Phase 7+.
    """

    async def run(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> int:
        """Return the number of bars that would be ingested."""
        # Phase 6 stub — returns 0 until adapter + DB wiring is complete
        return 0

    async def list_gaps(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[tuple[date, date]]:
        """Return date ranges where bars are missing from the DB."""
        return [(start, end)]
