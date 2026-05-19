"""MacroIngestionService — ingest and persist macro time series."""

from __future__ import annotations

from datetime import date

from app.clients.macro.base import MacroAdapter, MacroDataPoint


class MacroIngestionService:
    """Coordinates macro series fetching from a provider."""

    def __init__(self, adapter: MacroAdapter) -> None:
        self._adapter = adapter

    async def ingest_series(
        self,
        series_code: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> list[MacroDataPoint]:
        """Fetch observations for a single macro series."""
        return list(await self._adapter.fetch_series(series_code, start=start, end=end))

    async def list_available_series(self) -> list[str]:
        return await self._adapter.list_series()
