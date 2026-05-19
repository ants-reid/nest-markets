"""FRED macroeconomic data adapter."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from app.clients.macro.base import MacroAdapter, MacroDataPoint


class FREDAdapter(MacroAdapter):
    """Fetches economic time series from the Federal Reserve (FRED) API."""

    _BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "fred"

    async def fetch_series(
        self, series_code: str, *, start: date | None = None, end: date | None = None
    ) -> Sequence[MacroDataPoint]:
        raise NotImplementedError("FRED series fetch not yet implemented")

    async def list_series(self) -> list[str]:
        return ["FEDFUNDS", "CPIAUCSL", "UNRATE", "DGS10", "VIXCLS"]

    async def health_check(self) -> bool:
        return False
