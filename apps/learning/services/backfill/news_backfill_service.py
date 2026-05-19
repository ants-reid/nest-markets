"""NewsBackfillService — coordinate historical news ingestion."""

from __future__ import annotations

from typing import Sequence


class NewsBackfillService:
    """Fetches historical news and persists it idempotently by external_id."""

    async def run(
        self,
        symbols: Sequence[str],
        *,
        limit: int = 100,
    ) -> int:
        """Return the number of news records that would be ingested."""
        return 0
