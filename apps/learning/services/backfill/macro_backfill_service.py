"""MacroBackfillService — coordinate historical macro series ingestion."""

from __future__ import annotations

from datetime import date


class MacroBackfillService:
    """Fetches historical macro observations and persists them idempotently."""

    async def run(
        self,
        series_code: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> int:
        """Return the number of observations that would be ingested."""
        return 0
