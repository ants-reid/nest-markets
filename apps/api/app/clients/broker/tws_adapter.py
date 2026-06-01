"""Read-only TWS / IB Gateway socket broker adapter (P2 scaffold).

Submit, cancel, and modify are intentionally unimplemented and raise
NotImplementedError. The adapter is only constructible when the caller
explicitly selects the ``tws`` provider via the factory; the default
broker provider remains ``ibkr`` (Client Portal Gateway).

``ib_async`` is imported lazily so that app + test collection still
work when the package is not installed.
"""
from __future__ import annotations

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
    ) -> None:
        self._host = host
        self._port = int(port)
        self._client_id = int(client_id)
        self._account_id = account_id
        self._connect_timeout = float(connect_timeout)
        self._ib_factory = ib_factory or _default_ib_factory
        self._ib: Any | None = None
        self._lock = threading.Lock()

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
                readonly=True,
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
    async def get_account_info(self) -> AccountInfo:
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

    async def get_positions(self) -> list[PositionInfo]:
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

    # ------------------------------------------------------------------
    # Write surface — explicitly disabled in P2
    # ------------------------------------------------------------------
    async def submit_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError(_READ_ONLY_MSG)

    async def place_order(self, *args: Any, **kwargs: Any) -> OrderResult:
        raise NotImplementedError(_READ_ONLY_MSG)

    async def cancel_order(self, broker_order_id: str) -> bool:
        raise NotImplementedError(_READ_ONLY_MSG)

    async def modify_order(self, *args: Any, **kwargs: Any) -> OrderResult:
        raise NotImplementedError(_READ_ONLY_MSG)
