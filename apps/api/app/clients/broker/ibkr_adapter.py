"""IBKRAdapter — IB REST API 2.30.0 client.

Uses IB Client Portal Gateway (``cp-api-stable.jar``) via httpx.AsyncClient.
Paper/local gateway:   https://localhost:5000/v1/api
Live (OAuth):          https://api.ibkr.com/v1/api

Session flow (local gateway):
    1. connect()  → POST /iserver/auth/ssodh/init
                    GET  /iserver/accounts  (pre-flight + account selection)
                    POST /iserver/questions/suppress
    2. tickle()   → POST /tickle  (call every 60 s)
    3. disconnect()→ POST /logout

Key constraints (from IBKR Campus research 2026-04-24):
- Order body is a plain JSON **array** — NOT wrapped in {"orders": [...]}
- Modify order requires ALL original fields
- SMD WebSocket subscriptions auto-terminate after 10 minutes
- 429 response = 10-minute IP lockout — never burst requests
- US Futures require "manualIndicator": false
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

import httpx

from app.clients.broker.broker_interface import (
    AccountInfo,
    OrderRequest,
    OrderResult,
    PositionInfo,
)

_logger = logging.getLogger(__name__)

# Mapping from internal order-type strings to IBKR REST orderType values
_ORDER_TYPE_MAP: dict[str, str] = {
    "MARKET": "MKT",
    "LIMIT": "LMT",
    "STOP": "STP",
    "STOP_LIMIT": "STP LMT",
    "TRAIL": "TRAIL",
    "TRAIL_LIMIT": "TRAIL LIMIT",
}

# Standard order-reply message IDs to suppress for automation
_SUPPRESS_IDS = [
    "o163", "o354", "o382", "o383", "o403", "o451",
    "o2136", "o2137", "o2165", "o10082", "o10138",
    "o10151", "o10152", "o10153", "o10164", "o10223",
    "o10288", "o10331", "o10332", "o10333", "o10334",
    "o10335", "o10336", "p6", "p12",
]

# Snapshot field codes for top-of-book market data
_SNAPSHOT_FIELDS = "31,84,85,86,87,7295,7296,70,71"
# 31=last, 84=bid, 85=bidSize, 86=ask, 87=askSize,
# 7295=open, 7296=close, 70=high, 71=low


class IBKRAdapter:
    """IB REST API 2.30.0 broker adapter.

    Implements the :class:`~app.clients.broker.broker_interface.BrokerInterface`
    protocol using httpx against the IB Client Portal Gateway.

    Args:
        base_url:  Gateway base URL (without trailing slash).
                   Defaults to paper-trading local gateway.
        timeout:   Per-request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "https://localhost:5000/v1/api",
        timeout: float = 30.0,
        preferred_account_id: str | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._preferred_account_id = preferred_account_id
        self._client: httpx.AsyncClient | None = None
        self._account_id: str | None = None
        self._conid_cache: dict[str, int] = {}
        _logger.info(
            "IBKRAdapter created — base_url=%s preferred_account_id=%s",
            base_url,
            preferred_account_id,
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the gateway connection and initialise the brokerage session."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            verify=False,  # local gateway uses a self-signed cert
            timeout=self._timeout,
            follow_redirects=True,
        )
        # For the local gateway, /iserver/auth/ssodh/init starts the session.
        # The gateway handles SSODH automatically — we just need to call it.
        await self._client.post(
            "/iserver/auth/ssodh/init",
            json={"compete": False, "publish": True},
        )
        # Pre-flight: loads account data into gateway cache; returns account list
        resp = await self._client.get("/iserver/accounts")
        resp.raise_for_status()
        data = resp.json()
        accounts = data.get("accounts", [])
        selected = data.get("selectedAccount")
        if self._preferred_account_id and self._preferred_account_id in accounts:
            self._account_id = self._preferred_account_id
        else:
            self._account_id = selected or (accounts[0] if accounts else None)
        _logger.info("IBKRAdapter connected — account=%s", self._account_id)
        await self._suppress_order_replies()

    async def tickle(self) -> None:
        """Keep the gateway session alive. Call every 60 seconds."""
        resp = await self._request("POST", "/tickle")
        _logger.debug("tickle — session=%s", resp.get("session", "?"))

    async def disconnect(self) -> None:
        """Log out and close the HTTP client."""
        if self._client:
            try:
                await self._client.post("/logout")
            except Exception:  # noqa: BLE001
                pass
            await self._client.aclose()
            self._client = None
        self._account_id = None
        _logger.info("IBKRAdapter disconnected")

    @property
    def is_connected(self) -> bool:
        """True once :meth:`connect` has completed successfully."""
        return self._client is not None and self._account_id is not None

    @property
    def account_id(self) -> str | None:
        """Selected account ID after connect."""
        return self._account_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _suppress_order_replies(self) -> None:
        """Suppress all standard order-reply prompts for automation mode."""
        await self._client.post(
            "/iserver/questions/suppress",
            json={"messageIds": _SUPPRESS_IDS},
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Issue a request, retry once on 401 (session expired)."""
        assert self._client is not None, "Not connected — call connect() first"
        resp = await self._client.request(method, path, **kwargs)
        if resp.status_code == 401:
            _logger.warning("Session expired — reconnecting")
            await self.connect()
            resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:  # noqa: BLE001
            return {}

    async def _handle_order_replies(self, response: list[dict]) -> list[dict]:
        """Confirm any orderReplyMessage challenges in the response."""
        confirmed: list[dict] = []
        for item in response:
            if "id" in item and "message" in item:
                # orderReplyMessage — must confirm
                reply_id = item["id"]
                _logger.debug("Confirming order reply id=%s", reply_id)
                result = await self._request(
                    "POST",
                    f"/iserver/reply/{reply_id}",
                    json={"confirmed": True},
                )
                confirmed.extend(result if isinstance(result, list) else [result])
            else:
                confirmed.append(item)
        return confirmed

    # ------------------------------------------------------------------
    # Contract lookup
    # ------------------------------------------------------------------

    async def resolve_conid(self, symbol: str, sec_type: str = "STK") -> int:
        """Resolve ticker symbol to IBKR contract ID (conid).

        Results are cached in-process to avoid redundant API calls.
        """
        cache_key = f"{symbol}:{sec_type}"
        if cache_key in self._conid_cache:
            return self._conid_cache[cache_key]
        data = await self._request(
            "GET",
            "/iserver/secdef/search",
            params={"symbol": symbol, "secType": sec_type},
        )
        results = data if isinstance(data, list) else []
        if not results:
            raise ValueError(f"No contract found for symbol={symbol} secType={sec_type}")
        conid = int(results[0]["conid"])
        self._conid_cache[cache_key] = conid
        _logger.debug("Resolved %s -> conid=%d", symbol, conid)
        return conid

    # ------------------------------------------------------------------
    # Account & portfolio
    # ------------------------------------------------------------------

    async def get_account_info(self) -> AccountInfo:
        """Return account balance summary."""
        assert self._account_id, "Not connected"
        data = await self._request("GET", f"/iserver/account/{self._account_id}/summary")

        def _d(key: str) -> Decimal:
            val = data.get(key, {})
            amount = val.get("amount", 0) if isinstance(val, dict) else val
            return Decimal(str(amount))

        return AccountInfo(
            net_liquidation=_d("netLiquidationValue"),
            cash_balance=_d("totalCashValue"),
            buying_power=_d("buyingPower"),
            currency=data.get("currency", "USD"),
            excess_liquidity=_d("excessLiquidity"),
            margin=_d("maintenanceMargin"),
            unrealized_pnl=_d("unrealizedPnL"),
        )

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    async def get_positions(self) -> list[PositionInfo]:
        """Return all open positions for the account."""
        assert self._account_id, "Not connected"
        # pre-flight to load account data into gateway cache
        await self._request("GET", "/portfolio/accounts")
        data = await self._request(
            "GET", f"/portfolio2/{self._account_id}/positions"
        )
        positions = data if isinstance(data, list) else []
        result: list[PositionInfo] = []
        for p in positions:
            qty = Decimal(str(p.get("position", 0)))
            if qty == 0:
                continue
            result.append(
                PositionInfo(
                    conid=int(p.get("conid", 0)),
                    ticker=p.get("ticker", p.get("symbol", "")),
                    side="BUY" if qty > 0 else "SELL",
                    quantity=abs(qty),
                    avg_cost=Decimal(str(p.get("avgCost", p.get("avgPrice", 0)))),
                    market_price=Decimal(str(p.get("marketPrice", 0))) if p.get("marketPrice") else None,
                    market_value=Decimal(str(p.get("marketValue", 0))) if p.get("marketValue") else None,
                    unrealized_pnl=Decimal(str(p.get("unrealizedPnl", 0))),
                    realized_pnl=Decimal(str(p.get("realizedPnl", 0))),
                    asset_class=p.get("assetClass", "STK"),
                    currency=p.get("currency", "USD"),
                )
            )
        return result

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        """Submit a new order to IBKR.

        Resolves ticker to conid automatically. Maps :class:`OrderRequest`
        fields to the REST API body format (plain array, not wrapped object).
        """
        assert self._account_id, "Not connected"
        ibkr_order_type = _ORDER_TYPE_MAP.get(request.order_type, request.order_type)
        conid = await self.resolve_conid(request.ticker)
        coid = request.client_order_id or f"mh-{uuid.uuid4().hex[:12]}"

        order_body: dict[str, Any] = {
            "conid": conid,
            "secType": f"{conid}:STK",
            "orderType": ibkr_order_type,
            "side": request.side,
            "quantity": float(request.quantity),
            "tif": request.tif,
            "outsideRTH": request.outside_rth,
            "cOID": coid,
        }
        if request.limit_price is not None:
            order_body["price"] = float(request.limit_price)
        if request.stop_price is not None:
            order_body["auxPrice"] = float(request.stop_price)

        raw = await self._request(
            "POST",
            f"/iserver/account/{self._account_id}/orders",
            json=[order_body],
        )
        response_list = raw if isinstance(raw, list) else [raw]
        response_list = await self._handle_order_replies(response_list)
        first = response_list[0] if response_list else {}

        if "error" in first:
            return OrderResult(
                broker_order_id="",
                status="REJECTED",
                error_message=str(first["error"]),
            )

        return OrderResult(
            broker_order_id=str(first.get("order_id", "")),
            status=_map_ibkr_status(first.get("order_status", "")),
        )

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an open order. Returns True if successfully cancelled."""
        assert self._account_id, "Not connected"
        try:
            await self._request(
                "DELETE",
                f"/iserver/account/{self._account_id}/order/{broker_order_id}",
            )
            return True
        except httpx.HTTPStatusError as exc:
            _logger.warning("Cancel order %s failed: %s", broker_order_id, exc)
            return False

    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]:
        """Return raw order status dict from ``/iserver/account/order/status/{id}``."""
        return await self._request(
            "GET", f"/iserver/account/order/status/{broker_order_id}"
        )

    async def modify_order(
        self, broker_order_id: str, updated_fields: dict[str, Any]
    ) -> OrderResult:
        """Modify an existing order.

        ``updated_fields`` must contain **all** original order fields plus any
        changes — the REST API rejects partial updates.
        """
        assert self._account_id, "Not connected"
        raw = await self._request(
            "POST",
            f"/iserver/account/{self._account_id}/order/{broker_order_id}",
            json=updated_fields,
        )
        response_list = raw if isinstance(raw, list) else [raw]
        response_list = await self._handle_order_replies(response_list)
        first = response_list[0] if response_list else {}
        return OrderResult(
            broker_order_id=broker_order_id,
            status=_map_ibkr_status(first.get("order_status", "")),
        )

    # ------------------------------------------------------------------
    # Complex order types
    # ------------------------------------------------------------------

    async def submit_bracket_order(
        self,
        conid: int,
        side: str,
        quantity: float,
        entry_price: float,
        take_profit_price: float,
        stop_loss_price: float,
        tif: str = "DAY",
    ) -> list[OrderResult]:
        """Submit a bracket order (entry + take-profit + stop-loss) in one call.

        Returns a list of :class:`OrderResult` — one per leg.
        """
        assert self._account_id, "Not connected"
        parent_coid = f"bracket-{uuid.uuid4().hex[:12]}"
        exit_side = "SELL" if side == "BUY" else "BUY"
        body = [
            {
                "conid": conid, "secType": f"{conid}:STK",
                "orderType": "LMT", "side": side,
                "quantity": quantity, "price": entry_price,
                "tif": tif, "cOID": parent_coid,
            },
            {
                "conid": conid, "secType": f"{conid}:STK",
                "orderType": "LMT", "side": exit_side,
                "quantity": quantity, "price": take_profit_price,
                "tif": "GTC", "parentId": parent_coid,
            },
            {
                "conid": conid, "secType": f"{conid}:STK",
                "orderType": "STP", "side": exit_side,
                "quantity": quantity, "auxPrice": stop_loss_price,
                "tif": "GTC", "parentId": parent_coid,
            },
        ]
        raw = await self._request(
            "POST",
            f"/iserver/account/{self._account_id}/orders",
            json=body,
        )
        response_list = raw if isinstance(raw, list) else [raw]
        response_list = await self._handle_order_replies(response_list)
        return [
            OrderResult(
                broker_order_id=str(r.get("order_id", "")),
                status=_map_ibkr_status(r.get("order_status", "")),
            )
            for r in response_list
        ]

    async def submit_oca_order(
        self,
        legs: list[dict[str, Any]],
    ) -> list[OrderResult]:
        """Submit a One-Cancels-All (OCA) group.

        Each dict in ``legs`` should be a complete order body (conid, orderType,
        side, quantity, price/auxPrice, tif, cOID).  ``isSingleGroup`` is added
        automatically.
        """
        assert self._account_id, "Not connected"
        body = [{**leg, "isSingleGroup": True} for leg in legs]
        raw = await self._request(
            "POST",
            f"/iserver/account/{self._account_id}/orders",
            json=body,
        )
        response_list = raw if isinstance(raw, list) else [raw]
        response_list = await self._handle_order_replies(response_list)
        return [
            OrderResult(
                broker_order_id=str(r.get("order_id", "")),
                status=_map_ibkr_status(r.get("order_status", "")),
            )
            for r in response_list
        ]

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    async def get_snapshot(
        self,
        conids: list[int],
        fields: str = _SNAPSHOT_FIELDS,
    ) -> list[dict[str, Any]]:
        """Return a market-data snapshot for one or more conids.

        First call subscribes; may return empty — poll after 1–2 s if needed.
        Maximum 100 conids and 50 fields per call (IBKR limit Dec 2025).
        """
        assert len(conids) <= 100, "Maximum 100 conids per snapshot call"
        data = await self._request(
            "GET",
            "/iserver/marketdata/snapshot",
            params={"conids": ",".join(str(c) for c in conids), "fields": fields},
        )
        return data if isinstance(data, list) else []

    async def unsubscribe_snapshot(self, conid: int) -> None:
        """Unsubscribe a market-data snapshot for a single conid."""
        await self._request(
            "POST",
            "/iserver/marketdata/unsubscribe",
            json={"conid": str(conid)},
        )

    async def unsubscribe_all_snapshots(self) -> None:
        """Unsubscribe all active market-data snapshot subscriptions."""
        await self._request("GET", "/iserver/marketdata/unsubscribeall")

    async def get_history(
        self,
        conid: int,
        period: str = "1w",
        bar: str = "1h",
        outside_rth: bool = False,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Return historical OHLCV bars.

        Args:
            conid:       Contract ID.
            period:      Duration: 1d, 1w, 1m, 3m, 1y.
            bar:         Bar size: 1min, 5min, 1h, 1d, 1w.
            outside_rth: Include extended hours bars.
            source:      Optional (Feb 2026+): T=trades, B=bid, A=ask, M=midpoint.

        Returns dict with keys ``barLength``, ``data`` (list of OHLCV bars).
        Each bar: ``{o, h, l, c, v, t}`` where ``t`` is Unix timestamp ms.
        """
        params: dict[str, Any] = {
            "conid": conid,
            "period": period,
            "bar": bar,
            "outsideRth": outside_rth,
        }
        if source:
            params["source"] = source
        return await self._request("GET", "/iserver/marketdata/history", params=params)

    # ------------------------------------------------------------------
    # Options chain discovery
    # ------------------------------------------------------------------

    async def get_option_months(
        self, symbol: str, exchange: str = "SMART"
    ) -> tuple[int, list[str]]:
        """Step 1 of the options chain flow.

        Returns ``(underlying_conid, [month_codes])`` where month codes are
        e.g. ``["APR26", "MAY26", ...]``.
        """
        data = await self._request(
            "GET", "/iserver/secdef/search", params={"symbol": symbol}
        )
        results = data if isinstance(data, list) else []
        conid = int(results[0]["conid"])
        months: list[str] = []
        for sec in results[0].get("sections", []):
            if sec.get("secType") == "OPT":
                months = sec.get("months", "").split(";")
                break
        return conid, [m for m in months if m]

    async def get_option_strikes(
        self, underlying_conid: int, month: str, exchange: str = "SMART"
    ) -> dict[str, list[float]]:
        """Step 2: return ``{"call": [...], "put": [...]}`` strike lists."""
        return await self._request(
            "GET",
            "/iserver/secdef/strikes",
            params={
                "conid": underlying_conid,
                "sectype": "OPT",
                "month": month,
                "exchange": exchange,
            },
        )

    async def get_option_contracts(
        self,
        underlying_conid: int,
        month: str,
        right: str,
        strike: float,
        exchange: str = "SMART",
    ) -> list[dict[str, Any]]:
        """Step 3: return full contract details for a specific strike/right.

        Each item includes: conid, symbol, right, strike, maturityDate,
        multiplier, tradingClass, currency.
        """
        data = await self._request(
            "GET",
            "/iserver/secdef/info",
            params={
                "conid": underlying_conid,
                "sectype": "OPT",
                "month": month,
                "right": right,
                "exchange": exchange,
                "strike": strike,
            },
        )
        return data if isinstance(data, list) else []

    async def get_trades(self) -> list[dict[str, Any]]:
        """Fetch current-day trade executions.

        Calls GET /iserver/account/trades.
        Each item includes: orderId, order_ref, symbol, side, size,
        price, commission, net_amount, trade_time.

        Returns:
            List of raw execution dicts for today
        """
        data = await self._request("GET", "/iserver/account/trades")
        return data if isinstance(data, list) else []

    async def get_pnl(self) -> dict[str, Any]:
        """Fetch partitioned P&L for the account.

        Calls GET /iserver/account/pnl/partitioned.
        The response contains upnl dict keyed by "{accountId}.Core" with:
          dpl  — daily P&L
          upl  — unrealized P&L
          nl   — net liquidation

        Initial request may return empty upnl; the caller should poll once.

        Returns:
            Raw response dict: {"upnl": {"DU12345.Core": {"dpl": ..., "upl": ..., "nl": ...}}}
        """
        data = await self._request("GET", "/iserver/account/pnl/partitioned")
        return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_ibkr_status(ibkr_status: str) -> str:
    """Map IBKR order status string to internal canonical values."""
    _map = {
        "PreSubmitted": "SUBMITTED",
        "Submitted": "SUBMITTED",
        "Filled": "FILLED",
        "Cancelled": "CANCELLED",
        "PendingCancel": "CANCELLED",
        "Inactive": "REJECTED",
        "WarnState": "SUBMITTED",
    }
    return _map.get(ibkr_status, ibkr_status.upper() if ibkr_status else "UNKNOWN")

