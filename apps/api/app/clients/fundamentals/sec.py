"""SEC EDGAR fundamentals adapter."""

from __future__ import annotations


from app.clients.fundamentals.base import FundamentalsAdapter, FundamentalsRecord


class SECAdapter(FundamentalsAdapter):
    """Fetches company fundamentals from SEC EDGAR."""

    _BASE_URL = "https://data.sec.gov"

    @property
    def provider_name(self) -> str:
        return "sec_edgar"

    async def fetch_fundamentals(self, symbol: str) -> FundamentalsRecord:
        raise NotImplementedError("SEC EDGAR fundamentals not yet implemented")

    async def health_check(self) -> bool:
        return False
