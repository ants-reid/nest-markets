"""Base interface for all fundamentals data adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FundamentalsRecord:
    """Normalized company fundamentals snapshot."""

    symbol: str
    snapshot_date: date
    pe_ratio: float | None = None
    price_to_book: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    roa: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    dividend_yield: float | None = None
    free_cash_flow: float | None = None
    revenue: float | None = None
    earnings: float | None = None


class FundamentalsAdapter(ABC):
    """Abstract interface every fundamentals provider must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def fetch_fundamentals(self, symbol: str) -> FundamentalsRecord:
        """Fetch latest fundamentals snapshot for a symbol."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider endpoint is reachable."""
