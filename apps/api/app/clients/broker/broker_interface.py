"""BrokerInterface — abstract protocol defining broker client contract.

All concrete broker adapters (IBKR, Alpaca, paper trading, etc.) must
satisfy this protocol.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable


@dataclass
class OrderRequest:
    """Parameters for submitting a new order."""

    ticker: str
    side: str          # "BUY" | "SELL"
    quantity: Decimal
    order_type: str    # "MARKET" | "LIMIT" | "STOP" | "STOP_LIMIT" | "TRAIL"
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    tif: str = "DAY"   # time-in-force: DAY, GTC, IOC
    outside_rth: bool = False
    client_order_id: str | None = None


@dataclass
class OrderResult:
    """Broker response after submitting an order."""

    broker_order_id: str
    status: str        # "SUBMITTED" | "FILLED" | "REJECTED" | "CANCELLED"
    filled_price: Decimal | None = None
    filled_quantity: Decimal | None = None
    error_message: str | None = None
    submitted_at: datetime | None = None


@dataclass
class PositionInfo:
    """Single open position returned by the broker."""

    conid: int
    ticker: str
    side: str                   # "BUY" | "SELL"
    quantity: Decimal
    avg_cost: Decimal
    market_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    realized_pnl: Decimal | None = None
    asset_class: str = "STK"
    currency: str = "USD"


@dataclass
class AccountInfo:
    """Summary of account balances."""

    net_liquidation: Decimal
    cash_balance: Decimal
    buying_power: Decimal
    currency: str = "USD"
    excess_liquidity: Decimal = field(default_factory=lambda: Decimal("0"))
    margin: Decimal = field(default_factory=lambda: Decimal("0"))
    unrealized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))


@runtime_checkable
class BrokerInterface(Protocol):
    """Minimal contract for order execution and account queries."""

    async def submit_order(self, request: OrderRequest) -> OrderResult: ...

    async def cancel_order(self, broker_order_id: str) -> bool: ...

    async def get_account_info(self) -> AccountInfo: ...

    async def get_positions(self) -> list[PositionInfo]: ...


@runtime_checkable
class AdvancedOrderBroker(Protocol):
    """Broker contract for complex order submission flows."""

    async def submit_bracket_order(
        self,
        conid: int,
        side: str,
        quantity: float,
        entry_price: float,
        take_profit_price: float,
        stop_loss_price: float,
        tif: str = "DAY",
    ) -> list[OrderResult]: ...

    async def submit_oca_order(self, legs: list[dict[str, Any]]) -> list[OrderResult]: ...

    async def submit_order(self, request: OrderRequest) -> OrderResult: ...


@runtime_checkable
class ContractLookupBroker(Protocol):
    """Broker contract for symbol-to-contract resolution."""

    async def resolve_conid(self, symbol: str, sec_type: str = "STK") -> int: ...


@runtime_checkable
class MarketDataBroker(Protocol):
    """Broker contract for market data snapshots and history."""

    async def get_snapshot(self, conid: int, fields: str | None = None) -> dict[str, Any]: ...

    async def get_history(
        self,
        conid: int,
        period: str,
        bar: str = "1d",
        outside_rth: bool = False,
    ) -> list[dict[str, Any]]: ...

    async def unsubscribe_snapshot(self, conid: int) -> None: ...

    async def unsubscribe_all_snapshots(self) -> None: ...


@runtime_checkable
class PnLBroker(Protocol):
    """Broker contract for partitioned profit and loss retrieval."""

    async def get_pnl(self) -> dict[str, Any]: ...


@runtime_checkable
class TradeHistoryBroker(Protocol):
    """Broker contract for retrieving execution history."""

    async def get_trades(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class OptionChainBroker(Protocol):
    """Broker contract for option chain discovery."""

    async def get_option_months(self, conid: int) -> list[str]: ...

    async def get_option_strikes(self, conid: int, expiration: str) -> list[float]: ...

    async def get_option_contracts(
        self,
        conid: int,
        expiration: str,
        right: str = "CALL",
    ) -> list[dict[str, Any]]: ...
