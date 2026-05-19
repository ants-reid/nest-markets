"""QA-114: IBKRAdapter integration guard tests.

These tests confirm that the adapter correctly refuses to operate without a
live gateway connection (connect() not called), and that the BrokerInterface
protocol and dataclass contracts are still satisfied.

Full functional tests (session, orders, positions, market data, options chain)
are in tests/clients/test_ibkr_adapter.py (QA-115 through QA-122).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.clients.broker.broker_interface import (
    BrokerInterface,
    OrderRequest,
)
from app.clients.broker.ibkr_adapter import IBKRAdapter


def test_ibkr_adapter_satisfies_broker_interface():
    """IBKRAdapter must satisfy the BrokerInterface runtime-checkable protocol."""
    adapter = IBKRAdapter()
    assert isinstance(adapter, BrokerInterface)


@pytest.mark.asyncio
async def test_submit_order_requires_connection():
    """submit_order raises AssertionError when connect() has not been called."""
    adapter = IBKRAdapter()
    req = OrderRequest(ticker="AAPL", side="BUY", quantity=Decimal("10"), order_type="MARKET")
    with pytest.raises(AssertionError, match="Not connected"):
        await adapter.submit_order(req)


@pytest.mark.asyncio
async def test_cancel_order_requires_connection():
    """cancel_order raises AssertionError when connect() has not been called."""
    adapter = IBKRAdapter()
    with pytest.raises(AssertionError, match="Not connected"):
        await adapter.cancel_order("ord-001")


@pytest.mark.asyncio
async def test_get_account_info_requires_connection():
    """get_account_info raises AssertionError when connect() has not been called."""
    adapter = IBKRAdapter()
    with pytest.raises(AssertionError):
        await adapter.get_account_info()


@pytest.mark.asyncio
async def test_get_positions_requires_connection():
    """get_positions raises AssertionError when connect() has not been called."""
    adapter = IBKRAdapter()
    with pytest.raises(AssertionError):
        await adapter.get_positions()


def test_order_request_dataclass():
    req = OrderRequest(
        ticker="TSLA", side="SELL", quantity=Decimal("5"),
        order_type="LIMIT", limit_price=Decimal("250.00"),
    )
    assert req.ticker == "TSLA"
    assert req.limit_price == Decimal("250.00")
    assert req.tif == "DAY"
    assert req.outside_rth is False
    assert req.client_order_id is None
