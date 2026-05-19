"""Phase 5 — fundamentals adapter tests."""

from __future__ import annotations

import asyncio

import pytest

from app.clients.fundamentals.base import FundamentalsAdapter, FundamentalsRecord
from app.clients.fundamentals.mock import MockFundamentalsAdapter
from app.clients.fundamentals.sec import SECAdapter


def test_abstract_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        FundamentalsAdapter()  # type: ignore[abstract]


def test_sec_stub_raises():
    with pytest.raises(NotImplementedError):
        asyncio.run(SECAdapter().fetch_fundamentals("AAPL"))


def test_sec_provider_name():
    assert SECAdapter().provider_name == "sec_edgar"


def test_mock_provider_name():
    assert MockFundamentalsAdapter().provider_name == "mock"


def test_mock_returns_fundamentals_record():
    record = asyncio.run(
        MockFundamentalsAdapter().fetch_fundamentals("MSFT")
    )
    assert isinstance(record, FundamentalsRecord)
    assert record.symbol == "MSFT"
    assert record.pe_ratio is not None


def test_mock_health_check():
    ok = asyncio.run(MockFundamentalsAdapter().health_check())
    assert ok is True
