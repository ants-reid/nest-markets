"""Mock fundamentals adapter for testing."""

from __future__ import annotations

from datetime import date

from app.clients.fundamentals.base import FundamentalsAdapter, FundamentalsRecord


class MockFundamentalsAdapter(FundamentalsAdapter):
    """Deterministic mock fundamentals adapter."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def fetch_fundamentals(self, symbol: str) -> FundamentalsRecord:
        return FundamentalsRecord(
            symbol=symbol,
            snapshot_date=date.today(),
            pe_ratio=20.0,
            price_to_book=3.0,
            debt_to_equity=0.5,
            current_ratio=2.0,
            roe=0.15,
            roa=0.08,
            gross_margin=0.40,
            net_margin=0.12,
            revenue=1_000_000.0,
            earnings=120_000.0,
        )

    async def health_check(self) -> bool:
        return True
