"""Package init for fundamentals adapters."""

from __future__ import annotations

from app.clients.fundamentals.base import FundamentalsAdapter, FundamentalsRecord
from app.clients.fundamentals.mock import MockFundamentalsAdapter
from app.clients.fundamentals.sec import SECAdapter

__all__ = ["FundamentalsAdapter", "FundamentalsRecord", "MockFundamentalsAdapter", "SECAdapter"]
