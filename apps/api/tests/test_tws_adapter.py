"""Unit tests for the read-only TWS broker adapter (P2 scaffold).

ib_async is stubbed via a factory injection; no socket I/O is performed.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.clients.broker.broker_interface import (
    AccountInfo,
    OrderRequest,
    PositionInfo,
)
from app.clients.broker.gateway_factory import BrokerGatewayFactory
from app.clients.broker.ibkr_adapter import IBKRAdapter
from app.clients.broker.tws_adapter import TwsBroker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary_row(tag: str, value: str, currency: str = "USD") -> SimpleNamespace:
    return SimpleNamespace(tag=tag, value=value, currency=currency, account="DUP1")


def _make_position(
    symbol: str,
    quantity: float,
    avg_cost: float,
    sec_type: str = "STK",
    currency: str = "USD",
    conid: int = 1,
) -> SimpleNamespace:
    contract = SimpleNamespace(
        symbol=symbol, secType=sec_type, currency=currency, conId=conid
    )
    return SimpleNamespace(contract=contract, position=quantity, avgCost=avg_cost)


def _make_ib(summary_rows: list, positions: list) -> MagicMock:
    ib = MagicMock()
    ib.isConnected.return_value = False
    ib.managedAccounts.return_value = ["DUP1"]
    ib.accountSummary.return_value = summary_rows
    ib.positions.return_value = positions
    return ib


def _make_broker(ib: MagicMock) -> TwsBroker:
    return TwsBroker(
        host="127.0.0.1",
        port=4002,
        client_id=43,
        account_id="DUP1",
        ib_factory=lambda: ib,
    )


# ---------------------------------------------------------------------------
# Field-mapping tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_account_info_maps_fields_correctly() -> None:
    ib = _make_ib(
        summary_rows=[
            _make_summary_row("NetLiquidation", "100588.73"),
            _make_summary_row("AvailableFunds", "100000.00"),
            _make_summary_row("BuyingPower", "400000.00"),
            _make_summary_row("ExcessLiquidity", "99500.00"),
            _make_summary_row("MaintMarginReq", "1000.00"),
            _make_summary_row("UnrealizedPnL", "12.34"),
        ],
        positions=[],
    )
    broker = _make_broker(ib)

    info = await broker.get_account_info()

    assert isinstance(info, AccountInfo)
    assert info.net_liquidation == Decimal("100588.73")
    assert info.cash_balance == Decimal("100000.00")
    assert info.buying_power == Decimal("400000.00")
    assert info.excess_liquidity == Decimal("99500.00")
    assert info.margin == Decimal("1000.00")
    assert info.unrealized_pnl == Decimal("12.34")
    assert info.currency == "USD"
    ib.connect.assert_called_once_with(
        "127.0.0.1", 4002, clientId=43, readonly=True, timeout=15.0
    )


@pytest.mark.asyncio
async def test_get_positions_maps_fields_correctly() -> None:
    ib = _make_ib(
        summary_rows=[],
        positions=[
            _make_position("AAPL", 10, 180.5, conid=265598),
            _make_position("TSLA", -5, 200.0, conid=76792991),
        ],
    )
    broker = _make_broker(ib)

    positions = await broker.get_positions()

    assert len(positions) == 2
    aapl, tsla = positions
    assert isinstance(aapl, PositionInfo)
    assert aapl.conid == 265598
    assert aapl.ticker == "AAPL"
    assert aapl.side == "BUY"
    assert aapl.quantity == Decimal("10")
    assert aapl.avg_cost == Decimal("180.5")
    assert aapl.asset_class == "STK"
    assert aapl.currency == "USD"

    assert tsla.side == "SELL"
    assert tsla.quantity == Decimal("-5")


# ---------------------------------------------------------------------------
# Read-only enforcement (default: submit_enabled=False)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_order_raises_when_submit_disabled() -> None:
    broker = _make_broker(_make_ib([], []))
    req = OrderRequest(
        ticker="AAPL",
        side="BUY",
        quantity=Decimal("1"),
        order_type="LIMIT",
        limit_price=Decimal("50"),
    )
    with pytest.raises(NotImplementedError, match="TWS adapter is read-only"):
        await broker.submit_order(req)


@pytest.mark.asyncio
async def test_place_order_alias_raises_not_implemented() -> None:
    """``place_order`` remains a hard read-only stub even when submit is on."""
    broker = _make_broker(_make_ib([], []))
    with pytest.raises(NotImplementedError, match="TWS adapter is read-only"):
        await broker.place_order(
            OrderRequest(
                ticker="AAPL",
                side="BUY",
                quantity=Decimal("1"),
                order_type="LIMIT",
                limit_price=Decimal("50"),
            )
        )


@pytest.mark.asyncio
async def test_cancel_order_raises_not_implemented() -> None:
    broker = _make_broker(_make_ib([], []))
    with pytest.raises(NotImplementedError, match="TWS adapter is read-only"):
        await broker.cancel_order("abc")


@pytest.mark.asyncio
async def test_modify_order_raises_not_implemented() -> None:
    broker = _make_broker(_make_ib([], []))
    with pytest.raises(NotImplementedError, match="TWS adapter is read-only"):
        await broker.modify_order("abc", quantity=Decimal("2"))


# ---------------------------------------------------------------------------
# Guarded submit (submit_enabled=True) — LIMIT only
# ---------------------------------------------------------------------------

def _make_submit_broker(ib: MagicMock) -> TwsBroker:
    return TwsBroker(
        host="127.0.0.1",
        port=4002,
        client_id=43,
        account_id="DUP1",
        ib_factory=lambda: ib,
        submit_enabled=True,
    )


@pytest.mark.asyncio
async def test_submit_limit_order_returns_broker_order_id(monkeypatch: pytest.MonkeyPatch) -> None:
    ib = _make_ib([], [])
    trade = SimpleNamespace(
        order=SimpleNamespace(orderId=4242, permId=999),
        orderStatus=SimpleNamespace(status="Submitted", filled=0, avgFillPrice=0.0),
    )
    ib.placeOrder.return_value = trade
    ib.qualifyContracts.return_value = None
    ib.sleep = MagicMock(return_value=None)

    fake_ib_async = SimpleNamespace(
        LimitOrder=lambda action, totalQuantity, lmtPrice: SimpleNamespace(
            action=action,
            totalQuantity=totalQuantity,
            lmtPrice=lmtPrice,
            account=None,
            tif=None,
            outsideRth=None,
            transmit=None,
        ),
        Stock=lambda symbol, exch, ccy: SimpleNamespace(
            symbol=symbol, exchange=exch, currency=ccy
        ),
    )
    import sys
    monkeypatch.setitem(sys.modules, "ib_async", fake_ib_async)

    broker = _make_submit_broker(ib)
    result = await broker.submit_order(
        OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="LIMIT",
            limit_price=Decimal("50.00"),
            tif="DAY",
        )
    )

    assert result.broker_order_id == "4242"
    assert result.status == "Submitted"
    assert result.error_message is None
    ib.placeOrder.assert_called_once()
    # When submit is enabled, the socket connection must NOT be read-only.
    ib.connect.assert_called_once_with(
        "127.0.0.1", 4002, clientId=43, readonly=False, timeout=15.0
    )


@pytest.mark.asyncio
async def test_submit_market_order_returns_rejected_without_submit() -> None:
    ib = _make_ib([], [])
    broker = _make_submit_broker(ib)
    result = await broker.submit_order(
        OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="MARKET",
        )
    )
    assert result.status == "REJECTED"
    assert "LIMIT" in (result.error_message or "")
    ib.placeOrder.assert_not_called()


@pytest.mark.asyncio
async def test_submit_stop_order_returns_rejected_without_submit() -> None:
    ib = _make_ib([], [])
    broker = _make_submit_broker(ib)
    result = await broker.submit_order(
        OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="STOP",
            stop_price=Decimal("45.00"),
        )
    )
    assert result.status == "REJECTED"
    ib.placeOrder.assert_not_called()


@pytest.mark.asyncio
async def test_submit_limit_without_price_returns_rejected() -> None:
    ib = _make_ib([], [])
    broker = _make_submit_broker(ib)
    result = await broker.submit_order(
        OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="LIMIT",
        )
    )
    assert result.status == "REJECTED"
    assert "limit_price" in (result.error_message or "")
    ib.placeOrder.assert_not_called()


@pytest.mark.asyncio
async def test_submit_limit_order_returns_rejected_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ib = _make_ib([], [])
    ib.placeOrder.side_effect = RuntimeError("boom")
    ib.qualifyContracts.return_value = None
    ib.sleep = MagicMock(return_value=None)

    fake_ib_async = SimpleNamespace(
        LimitOrder=lambda **kwargs: SimpleNamespace(
            account=None, tif=None, outsideRth=None, transmit=None, **kwargs
        ),
        Stock=lambda symbol, exch, ccy: SimpleNamespace(
            symbol=symbol, exchange=exch, currency=ccy
        ),
    )
    import sys
    monkeypatch.setitem(sys.modules, "ib_async", fake_ib_async)

    broker = _make_submit_broker(ib)
    result = await broker.submit_order(
        OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="LIMIT",
            limit_price=Decimal("50"),
        )
    )
    assert result.status == "REJECTED"
    assert "boom" in (result.error_message or "")


# ---------------------------------------------------------------------------
# Factory branching
# ---------------------------------------------------------------------------

def test_factory_creates_tws_adapter_when_explicitly_selected() -> None:
    broker = BrokerGatewayFactory.create("tws")
    assert isinstance(broker, TwsBroker)


def test_factory_creates_tws_socket_alias() -> None:
    broker = BrokerGatewayFactory.create("tws_socket")
    assert isinstance(broker, TwsBroker)


def test_factory_default_ibkr_unchanged() -> None:
    broker = BrokerGatewayFactory.create("ibkr")
    assert isinstance(broker, IBKRAdapter)


def test_factory_paper_still_raises() -> None:
    with pytest.raises(NotImplementedError):
        BrokerGatewayFactory.create("paper")


def test_factory_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError):
        BrokerGatewayFactory.create("totally_made_up")  # type: ignore[arg-type]


def test_default_broker_provider_setting_unchanged() -> None:
    """The default ``broker_provider`` setting MUST remain ``ibkr``;
    adding the TWS branch must not switch default routing."""
    from app.config import Settings

    assert Settings.model_fields["broker_provider"].default == "ibkr"


def test_tws_settings_defaults() -> None:
    from app.config import Settings

    assert Settings.model_fields["tws_host"].default == "127.0.0.1"
    assert Settings.model_fields["tws_port"].default == 4002
    assert Settings.model_fields["tws_client_id"].default == 43
    assert Settings.model_fields["tws_enabled"].default is False
