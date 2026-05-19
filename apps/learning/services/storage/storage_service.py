"""StorageService — thin abstraction over DB persistence for the learning app.

Phase 6 stub: no live DB connection.  Methods document the intended contract
and will be wired to a real SQLAlchemy session in Phase 7+.
"""

from __future__ import annotations

from typing import Any


class StorageService:
    """Persist ingested records to the database.

    The service is intentionally thin: it receives already-normalised
    domain objects and upserts them using the ORM session factory from
    ``apps/api``.
    """

    async def upsert_bars(self, rows: list[dict[str, Any]]) -> int:
        """Upsert OHLCV bars.  Returns number of rows affected."""
        return 0

    async def upsert_news(self, rows: list[dict[str, Any]]) -> int:
        """Upsert news articles by ``external_id``."""
        return 0

    async def upsert_macro_observations(self, rows: list[dict[str, Any]]) -> int:
        """Upsert macro observations by (series_code, observation_date)."""
        return 0

    async def upsert_fundamentals(self, rows: list[dict[str, Any]]) -> int:
        """Upsert fundamentals snapshots by (symbol, snapshot_date)."""
        return 0
