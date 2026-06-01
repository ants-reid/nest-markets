"""TWS / IB Gateway socket broker adapter.

The adapter is read-only by default. Submit is only enabled when the
caller passes ``submit_enabled=True`` AND uses the factory branch that
is explicitly selected via ``BROKER_PROVIDER=tws`` + ``TWS_ENABLED=true``.
With ``submit_enabled=False`` the socket connection itself is opened in
IBKR's ``readonly=True`` mode for defence-in-depth.

Only LIMIT orders are supported in the first guarded write cut. Any other
order type returns a safe REJECTED ``OrderResult`` rather than submitting.

``ib_async`` is imported lazily so that app + test collection still
work when the package is not installed.
"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from app.clients.broker.broker_interface import (
    AccountInfo,
    OrderRequest,
    OrderResult,
    PositionInfo,
)


_READ_ONLY_MSG = "TWS adapter is read-only"
_SUBMIT_DISABLED_MSG = "TWS adapter submit is disabled"
_UNSUPPORTED_ORDER_TYPE_MSG = (
    "TWS adapter currently supports LIMIT orders only"
)


def _default_ib_factory() -> Any:
    """Lazy import ib_async only when an instance is actually needed."""
    from ib_async import IB  # type: ignore[import-not-found]

    return IB()


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


class TwsBroker:
    """Read-only adapter over the TWS / IB Gateway socket API."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4002,
        client_id: int = 43,
        account_id: str | None = None,
        connect_timeout: float = 15.0,
        ib_factory: Callable[[], Any] | None = None,
        submit_enabled: bool = False,
    ) -> None:
        self._host = host
        self._port = int(port)
        self._client_id = int(client_id)
        self._account_id = account_id
        self._connect_timeout = float(connect_timeout)
        self._ib_factory = ib_factory or _default_ib_factory
        self._ib: Any | None = None
        self._lock = threading.Lock()
        self._submit_enabled = bool(submit_enabled)

    # ------------------------------------------------------------------
    # Connection lifecycle (lazy, read-only)
    # ------------------------------------------------------------------
    def _ensure_connected(self) -> Any:
        with self._lock:
            ib = self._ib
            if ib is not None and getattr(ib, "isConnected", lambda: False)():
                return ib
            ib = self._ib_factory()
            ib.connect(
                self._host,
                self._port,
                clientId=self._client_id,
                readonly=not self._submit_enabled,
                timeout=self._connect_timeout,
            )
            self._ib = ib
            return ib

    def disconnect(self) -> None:
        with self._lock:
            ib = self._ib
            self._ib = None
        if ib is not None and getattr(ib, "isConnected", lambda: False)():
            try:
                ib.disconnect()
            except Exception:
                pass

    def _resolve_account(self, ib: Any) -> str:
        if self._account_id:
            return self._account_id
        accounts = list(ib.managedAccounts() or [])
        if not accounts:
            raise RuntimeError("TWS returned no managed accounts")
        return accounts[0]

    # ------------------------------------------------------------------
    # Read-only BrokerInterface surface
    # ------------------------------------------------------------------
    def _get_account_info_blocking(self) -> AccountInfo:
        ib = self._ensure_connected()
        account = self._resolve_account(ib)
        rows = ib.accountSummary(account) or []

        wanted: dict[str, Any] = {
            "NetLiquidation": None,
            "AvailableFunds": None,
            "BuyingPower": None,
            "ExcessLiquidity": None,
            "MaintMarginReq": None,
            "UnrealizedPnL": None,
        }
        currency: str | None = None
        for row in rows:
            tag = getattr(row, "tag", None)
            if tag in wanted and wanted[tag] is None:
                wanted[tag] = getattr(row, "value", None)
                currency = currency or getattr(row, "currency", None)

        return AccountInfo(
            net_liquidation=_to_decimal(wanted["NetLiquidation"]),
            cash_balance=_to_decimal(wanted["AvailableFunds"]),
            buying_power=_to_decimal(wanted["BuyingPower"]),
            currency=currency or "USD",
            excess_liquidity=_to_decimal(wanted["ExcessLiquidity"]),
            margin=_to_decimal(wanted["MaintMarginReq"]),
            unrealized_pnl=_to_decimal(wanted["UnrealizedPnL"]),
        )

    async def get_account_info(self) -> AccountInfo:
        # ib_async sync wrappers drive their own event loop, so offload
        # connect + accountSummary onto a worker thread.
        return await asyncio.to_thread(self._get_account_info_blocking)

    def _get_positions_blocking(self) -> list[PositionInfo]:
        ib = self._ensure_connected()
        account = self._resolve_account(ib)
        positions = ib.positions(account) or []

        result: list[PositionInfo] = []
        for pos in positions:
            contract = getattr(pos, "contract", None)
            symbol = getattr(contract, "symbol", "") if contract is not None else ""
            sec_type = (
                getattr(contract, "secType", "STK") if contract is not None else "STK"
            )
            currency = (
                getattr(contract, "currency", "USD") if contract is not None else "USD"
            )
            conid_raw = getattr(contract, "conId", 0) if contract is not None else 0
            try:
                conid = int(conid_raw or 0)
            except (TypeError, ValueError):
                conid = 0

            qty = _to_decimal(getattr(pos, "position", 0))
            side = "BUY" if qty >= 0 else "SELL"
            result.append(
                PositionInfo(
                    conid=conid,
                    ticker=str(symbol or ""),
                    side=side,
                    quantity=qty,
                    avg_cost=_to_decimal(getattr(pos, "avgCost", 0)),
                    asset_class=str(sec_type or "STK"),
                    currency=str(currency or "USD"),
                )
            )
        return result

    async def get_positions(self) -> list[PositionInfo]:
        return await asyncio.to_thread(self._get_positions_blocking)

    # ------------------------------------------------------------------
    # Write surface — guarded by ``submit_enabled``; LIMIT only
    # ------------------------------------------------------------------
    async def submit_order(self, request: OrderRequest) -> OrderResult:
        if not self._submit_enabled:
            raise NotImplementedError(_READ_ONLY_MSG)
        order_type = (request.order_type or "").upper()
        if order_type != "LIMIT":
            return OrderResult(
                broker_order_id="",
                status="REJECTED",
                error_message=_UNSUPPORTED_ORDER_TYPE_MSG,
            )
        if request.limit_price is None:
            return OrderResult(
                broker_order_id="",
                status="REJECTED",
                error_message="LIMIT order requires limit_price",
            )
        return await asyncio.to_thread(self._submit_limit_blocking, request)

    def _submit_limit_blocking(self, request: OrderRequest) -> OrderResult:
        try:
            from ib_async import LimitOrder, Stock  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            return OrderResult(
                broker_order_id="",
                status="REJECTED",
                error_message=f"ib_async unavailable: {exc}",
            )

        try:
            ib = self._ensure_connected()
            account = self._resolve_account(ib)
            contract = Stock(request.ticker, "SMART", "USD")
            qualify = getattr(ib, "qualifyContracts", None)
            if callable(qualify):
                qualify(contract)
            order = LimitOrder(
                action=request.side,
                totalQuantity=float(request.quantity),
                lmtPrice=float(request.limit_price),
            )
            order.account = account
            order.tif = request.tif or "DAY"
            order.outsideRth = bool(request.outside_rth)
            order.transmit = True
            trade = ib.placeOrder(contract, order)
            sleep = getattr(ib, "sleep", None)
            if callable(sleep):
                sleep(1.0)
            order_id = getattr(getattr(trade, "order", None), "orderId", None) or getattr(
                getattr(trade, "order", None), "permId", None
            )
            status_obj = getattr(trade, "orderStatus", None)
            status = (getattr(status_obj, "status", None) or "SUBMITTED")
            filled = _to_decimal(getattr(status_obj, "filled", 0)) if status_obj else None
            avg_fill = getattr(status_obj, "avgFillPrice", None) if status_obj else None
            return OrderResult(
                broker_order_id=str(order_id or ""),
                status=str(status),
                filled_price=_to_decimal(avg_fill) if avg_fill else None,
                filled_quantity=filled,
                error_message=None,
            )
        except Exception as exc:  # noqa: BLE001
            return OrderResult(
                broker_order_id="",
                status="REJECTED",
                error_message=str(exc),
            )

    async def place_order(self, *args: Any, **kwargs: Any) -> OrderResult:
        raise NotImplementedError(_READ_ONLY_MSG)

    async def cancel_order(self, broker_order_id: str) -> bool:
        raise NotImplementedError(_READ_ONLY_MSG)

    async def modify_order(self, *args: Any, **kwargs: Any) -> OrderResult:
        raise NotImplementedError(_READ_ONLY_MSG)
