"""Base interface for all macroeconomic data adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class MacroDataPoint:
    """Single observation for a macro time series."""

    series_code: str
    observation_date: date
    value: float
    units: str | None = None


class MacroAdapter(ABC):
    """Abstract interface every macro data provider must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def fetch_series(
        self,
        series_code: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> Sequence[MacroDataPoint]:
        """Fetch observations for a macro time series."""

    @abstractmethod
    async def list_series(self) -> list[str]:
        """Return list of available series codes."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider endpoint is reachable."""
