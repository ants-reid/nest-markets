"""Mock macro adapter for testing."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from app.clients.macro.base import MacroAdapter, MacroDataPoint

_MOCK_SERIES = {
    "FEDFUNDS": 5.25,
    "CPIAUCSL": 315.2,
    "UNRATE": 3.9,
    "DGS10": 4.4,
    "VIXCLS": 18.0,
}


class MockMacroAdapter(MacroAdapter):
    """Deterministic mock macro adapter for unit tests."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def fetch_series(
        self, series_code: str, *, start: date | None = None, end: date | None = None
    ) -> Sequence[MacroDataPoint]:
        base_value = _MOCK_SERIES.get(series_code, 100.0)
        obs_start = start or date(2020, 1, 1)
        obs_end = end or date.today()
        points = []
        current = obs_start
        while current <= obs_end:
            points.append(MacroDataPoint(
                series_code=series_code,
                observation_date=current,
                value=base_value,
            ))
            current = date(current.year + (current.month // 12), (current.month % 12) + 1, 1)
        return points

    async def list_series(self) -> list[str]:
        return list(_MOCK_SERIES.keys())

    async def health_check(self) -> bool:
        return True
