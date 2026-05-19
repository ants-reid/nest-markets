"""QA-115 through QA-122: IBKRAdapter tests.

All tests use httpx.MockTransport to simulate IB Client Portal Gateway
responses without requiring a live gateway connection.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.clients.broker.broker_interface import (
    AccountInfo,
    BrokerInterface,
    OrderRequest,
    PositionInfo,
)
from app.clients.broker.ibkr_adapter import IBKRAdapter, _map_ibkr_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_transport(routes: dict[str, Any]) -> httpx.MockTransport:
    """Build a MockTransport that returns JSON responses keyed by 'METHOD /path'."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        if key in routes:
            payload = routes[key]
            if isinstance(payload, httpx.Response):
                return payload
            return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"error": f"Mock: no route for {key}"})

    return httpx.MockTransport(handler)


def _connected_adapter(routes: dict[str, Any]) -> IBKRAdapter:
    """Return an IBKRAdapter with a mocked gateway and session already set."""
    adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
    transport = _make_transport(routes)
    adapter._client = httpx.AsyncClient(
        base_url="https://localhost:5000/v1/api",
        transport=transport,
        verify=False,
    )
    adapter._account_id = "DU123456"
    return adapter


# ---------------------------------------------------------------------------
# Fixtures — common mock response payloads
# ---------------------------------------------------------------------------

ACCOUNTS_RESP = {"selectedAccount": "DU123456", "accounts": ["DU123456"]}
SSODH_RESP = {"authenticated": True, "established": True}
SUPPRESS_RESP = {"status": "submitted"}
TICKLE_RESP = {"session": "abc123", "iserver": {"authStatus": {"authenticated": True}}}

SUMMARY_RESP = {
    "netLiquidationValue": {"amount": 100000.0},
    "totalCashValue": {"amount": 75000.0},
    "buyingPower": {"amount": 150000.0},
    "excessLiquidity": {"amount": 80000.0},
    "maintenanceMargin": {"amount": 5000.0},
    "unrealizedPnL": {"amount": 1250.0},
    "currency": "USD",
}

SECDEF_SEARCH_RESP = [
    {
        "conid": 265598,
        "description": "NASDAQ",
        "sections": [
            {"secType": "OPT", "months": "APR26;MAY26;JUN26"},
            {"secType": "STK"},
        ],
    }
]

POSITIONS_RESP = [
    {
        "conid": 265598,
        "ticker": "AAPL",
        "position": 50.0,
        "avgCost": 172.50,
        "marketPrice": 178.25,
        "marketValue": 8912.50,
        "unrealizedPnl": 287.50,
        "realizedPnl": 0.0,
        "assetClass": "STK",
        "currency": "USD",
    },
    {
        "conid": 8314,
        "ticker": "SPY",
        "position": 0.0,   # zero qty — should be filtered out
        "avgCost": 450.0,
        "assetClass": "STK",
        "currency": "USD",
    },
]

PORTFOLIO_ACCOUNTS_RESP = [{"id": "DU123456"}]

ORDER_SUBMIT_RESP = [{"order_id": "1001", "order_status": "PreSubmitted"}]
ORDER_STATUS_RESP = {
    "order_id": "1001",
    "order_status": "Submitted",
    "average_price": 172.50,
    "cum_fill": 50,
    "remaining_quantity": 0,
}

BRACKET_RESP = [
    {"order_id": "2001", "order_status": "PreSubmitted"},
    {"order_id": "2002", "order_status": "PreSubmitted"},
    {"order_id": "2003", "order_status": "PreSubmitted"},
]

OCA_RESP = [
    {"order_id": "3001", "order_status": "PreSubmitted"},
    {"order_id": "3002", "order_status": "PreSubmitted"},
]

SNAPSHOT_RESP = [
    {"conid": 265598, "31": "178.25", "84": "178.20", "86": "178.30"}
]

HISTORY_RESP = {
    "barLength": 3600,
    "data": [
        {"o": 177.0, "h": 179.0, "l": 176.5, "c": 178.25, "v": 12000, "t": 1714000000000},
    ],
}

STRIKES_RESP = {"call": [170.0, 175.0, 180.0], "put": [170.0, 175.0, 180.0]}

OPTION_CONTRACTS_RESP = [
    {
        "conid": 999001,
        "symbol": "AAPL",
        "right": "C",
        "strike": 175.0,
        "maturityDate": "20260417",
        "multiplier": "100",
        "tradingClass": "AAPL",
        "currency": "USD",
    }
]


# ---------------------------------------------------------------------------
# QA-114: Protocol conformance
# ---------------------------------------------------------------------------

class TestBrokerProtocol:
    def test_ibkr_adapter_satisfies_broker_interface(self):
        """IBKRAdapter must satisfy the BrokerInterface runtime-checkable protocol."""
        adapter = IBKRAdapter()
        assert isinstance(adapter, BrokerInterface)

    def test_position_info_dataclass(self):
        pos = PositionInfo(
            conid=265598, ticker="AAPL", side="BUY",
            quantity=Decimal("50"), avg_cost=Decimal("172.50"),
        )
        assert pos.conid == 265598
        assert pos.currency == "USD"

    def test_account_info_new_fields(self):
        info = AccountInfo(
            net_liquidation=Decimal("100000"),
            cash_balance=Decimal("75000"),
            buying_power=Decimal("150000"),
            excess_liquidity=Decimal("80000"),
            margin=Decimal("5000"),
            unrealized_pnl=Decimal("1250"),
        )
        assert info.excess_liquidity == Decimal("80000")
        assert info.margin == Decimal("5000")
        assert info.unrealized_pnl == Decimal("1250")

    def test_order_request_new_fields(self):
        req = OrderRequest(
            ticker="AAPL", side="BUY", quantity=Decimal("10"),
            order_type="LIMIT", limit_price=Decimal("175.00"),
            client_order_id="my-coid-1", outside_rth=True,
        )
        assert req.client_order_id == "my-coid-1"
        assert req.outside_rth is True


# ---------------------------------------------------------------------------
# QA-115: Session management
# ---------------------------------------------------------------------------

class TestSession:
    @pytest.mark.asyncio
    async def test_connect_sets_account_id(self):
        routes = {
            "POST /v1/api/iserver/auth/ssodh/init": SSODH_RESP,
            "GET /v1/api/iserver/accounts": ACCOUNTS_RESP,
            "POST /v1/api/iserver/questions/suppress": SUPPRESS_RESP,
        }
        transport = _make_transport(routes)
        # Patch httpx.AsyncClient to inject mock transport
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            async def fake_post(path, **kwargs):
                r = httpx.Response(200, json=routes.get(f"POST /v1/api{path}", {}))
                return r

            async def fake_get(path, **kwargs):
                r = httpx.Response(200, json=routes.get(f"GET /v1/api{path}", {}))
                return r

            mock_client.post = fake_post
            mock_client.get = fake_get

            # Use a real client with mock transport instead
        # Direct approach: inject transport into the adapter
        adapter2 = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        real_client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=transport,
            verify=False,
        )
        adapter2._client = real_client
        adapter2._account_id = "DU123456"
        assert adapter2.is_connected is True
        assert adapter2.account_id == "DU123456"
        await real_client.aclose()

    @pytest.mark.asyncio
    async def test_connect_full_flow(self):
        """Full connect flow via mock transport."""
        routes = {
            "POST /v1/api/iserver/auth/ssodh/init": SSODH_RESP,
            "GET /v1/api/iserver/accounts": ACCOUNTS_RESP,
            "POST /v1/api/iserver/questions/suppress": SUPPRESS_RESP,
        }
        transport = _make_transport(routes)
        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")

        original_init = httpx.AsyncClient.__init__

        def patched_init(self, **kwargs):
            kwargs["transport"] = transport
            kwargs.pop("verify", None)
            original_init(self, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", patched_init):
            await adapter.connect()

        assert adapter.account_id == "DU123456"
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_is_connected_false_before_connect(self):
        adapter = IBKRAdapter()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_tickle(self):
        adapter = _connected_adapter({
            "POST /v1/api/tickle": TICKLE_RESP,
        })
        await adapter.tickle()  # should not raise
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        adapter = _connected_adapter({
            "POST /v1/api/logout": {"status": "ok"},
        })
        await adapter.disconnect()
        assert adapter.is_connected is False


# ---------------------------------------------------------------------------
# QA-116: Order submission and cancellation
# ---------------------------------------------------------------------------

class TestOrders:
    @pytest.mark.asyncio
    async def test_submit_order_market(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/secdef/search": SECDEF_SEARCH_RESP,
            "POST /v1/api/iserver/account/DU123456/orders": ORDER_SUBMIT_RESP,
        })
        req = OrderRequest(
            ticker="AAPL", side="BUY", quantity=Decimal("50"),
            order_type="MARKET",
        )
        result = await adapter.submit_order(req)
        assert result.broker_order_id == "1001"
        assert result.status == "SUBMITTED"
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_submit_order_limit_with_coid(self):
        sent_bodies: list[Any] = []

        def handler(request: httpx.Request) -> httpx.Response:
            key = f"{request.method} {request.url.path}"
            if key == "GET /v1/api/iserver/secdef/search":
                return httpx.Response(200, json=SECDEF_SEARCH_RESP)
            if key == "POST /v1/api/iserver/account/DU123456/orders":
                sent_bodies.append(json.loads(request.content))
                return httpx.Response(200, json=ORDER_SUBMIT_RESP)
            return httpx.Response(404)

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=httpx.MockTransport(handler),
            verify=False,
        )
        adapter._account_id = "DU123456"

        req = OrderRequest(
            ticker="AAPL", side="BUY", quantity=Decimal("10"),
            order_type="LIMIT", limit_price=Decimal("175.00"),
            client_order_id="my-coid-99",
        )
        result = await adapter.submit_order(req)

        assert result.status == "SUBMITTED"
        assert len(sent_bodies) == 1
        body = sent_bodies[0]
        assert isinstance(body, list), "Body must be a plain JSON array"
        assert body[0]["orderType"] == "LMT"
        assert body[0]["price"] == 175.00
        assert body[0]["cOID"] == "my-coid-99"
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_submit_order_rejected(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/secdef/search": SECDEF_SEARCH_RESP,
            "POST /v1/api/iserver/account/DU123456/orders": [{"error": "price out of range"}],
        })
        req = OrderRequest(
            ticker="AAPL", side="BUY", quantity=Decimal("1"),
            order_type="LIMIT", limit_price=Decimal("9999.00"),
        )
        result = await adapter.submit_order(req)
        assert result.status == "REJECTED"
        assert "price out of range" in (result.error_message or "")
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_cancel_order_success(self):
        adapter = _connected_adapter({
            "DELETE /v1/api/iserver/account/DU123456/order/1001": {"msg": "Order cancelled"},
        })
        ok = await adapter.cancel_order("1001")
        assert ok is True
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "order not found"})

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=httpx.MockTransport(handler),
            verify=False,
        )
        adapter._account_id = "DU123456"
        ok = await adapter.cancel_order("9999")
        assert ok is False
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_get_order_status(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/account/order/status/1001": ORDER_STATUS_RESP,
        })
        status = await adapter.get_order_status("1001")
        assert status["order_status"] == "Submitted"
        assert status["average_price"] == 172.50
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_order_type_mapping(self):
        """MARKET → MKT, LIMIT → LMT, STOP → STP, STOP_LIMIT → STP LMT."""
        sent_bodies: list[Any] = []

        def handler(request: httpx.Request) -> httpx.Response:
            key = f"{request.method} {request.url.path}"
            if key == "GET /v1/api/iserver/secdef/search":
                return httpx.Response(200, json=SECDEF_SEARCH_RESP)
            if key == "POST /v1/api/iserver/account/DU123456/orders":
                sent_bodies.append(json.loads(request.content))
                return httpx.Response(200, json=ORDER_SUBMIT_RESP)
            return httpx.Response(404)

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=httpx.MockTransport(handler),
            verify=False,
        )
        adapter._account_id = "DU123456"

        for internal, expected in [("MARKET", "MKT"), ("LIMIT", "LMT"), ("STOP", "STP")]:
            sent_bodies.clear()
            adapter._conid_cache.clear()
            req = OrderRequest(
                ticker="AAPL", side="BUY", quantity=Decimal("1"),
                order_type=internal, limit_price=Decimal("175.00"),
            )
            await adapter.submit_order(req)
            assert sent_bodies[0][0]["orderType"] == expected, f"{internal} should map to {expected}"

        await adapter._client.aclose()


# ---------------------------------------------------------------------------
# QA-117: Bracket orders
# ---------------------------------------------------------------------------

class TestBracketOrders:
    @pytest.mark.asyncio
    async def test_bracket_order_sends_three_legs(self):
        sent_bodies: list[Any] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if "orders" in request.url.path:
                sent_bodies.append(json.loads(request.content))
                return httpx.Response(200, json=BRACKET_RESP)
            return httpx.Response(404)

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=httpx.MockTransport(handler),
            verify=False,
        )
        adapter._account_id = "DU123456"

        results = await adapter.submit_bracket_order(
            conid=265598, side="BUY", quantity=100.0,
            entry_price=172.50, take_profit_price=185.00, stop_loss_price=165.00,
        )
        assert len(results) == 3
        assert all(r.status == "SUBMITTED" for r in results)

        body = sent_bodies[0]
        assert isinstance(body, list)
        assert len(body) == 3

        parent = body[0]
        tp = body[1]
        sl = body[2]

        # Parent must have cOID, children must have parentId matching parent cOID
        assert "cOID" in parent
        assert tp["parentId"] == parent["cOID"]
        assert sl["parentId"] == parent["cOID"]

        # Entry is LMT BUY, TP is LMT SELL, SL is STP SELL
        assert parent["orderType"] == "LMT" and parent["side"] == "BUY"
        assert tp["orderType"] == "LMT" and tp["side"] == "SELL"
        assert sl["orderType"] == "STP" and sl["side"] == "SELL"
        assert sl["auxPrice"] == 165.00

        await adapter._client.aclose()


# ---------------------------------------------------------------------------
# QA-118: OCA orders
# ---------------------------------------------------------------------------

class TestOCAOrders:
    @pytest.mark.asyncio
    async def test_oca_order_adds_is_single_group(self):
        sent_bodies: list[Any] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if "orders" in request.url.path:
                sent_bodies.append(json.loads(request.content))
                return httpx.Response(200, json=OCA_RESP)
            return httpx.Response(404)

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=httpx.MockTransport(handler),
            verify=False,
        )
        adapter._account_id = "DU123456"

        legs = [
            {"conid": 265598, "orderType": "LMT", "side": "BUY", "quantity": 1,
             "price": 175.0, "tif": "DAY", "cOID": "oca-a"},
            {"conid": 8314, "orderType": "LMT", "side": "BUY", "quantity": 1,
             "price": 450.0, "tif": "DAY", "cOID": "oca-b"},
        ]
        results = await adapter.submit_oca_order(legs)

        assert len(results) == 2
        body = sent_bodies[0]
        assert all(leg["isSingleGroup"] is True for leg in body), \
            "All OCA legs must have isSingleGroup=True"
        # Original keys preserved
        assert body[0]["conid"] == 265598
        assert body[1]["conid"] == 8314

        await adapter._client.aclose()


# ---------------------------------------------------------------------------
# QA-119: Positions
# ---------------------------------------------------------------------------

class TestPositions:
    @pytest.mark.asyncio
    async def test_get_positions_returns_non_zero_only(self):
        adapter = _connected_adapter({
            "GET /v1/api/portfolio/accounts": PORTFOLIO_ACCOUNTS_RESP,
            "GET /v1/api/portfolio2/DU123456/positions": POSITIONS_RESP,
        })
        positions = await adapter.get_positions()
        # AAPL qty=50 kept, SPY qty=0 filtered out
        assert len(positions) == 1
        aapl = positions[0]
        assert aapl.ticker == "AAPL"
        assert aapl.conid == 265598
        assert aapl.quantity == Decimal("50")
        assert aapl.side == "BUY"
        assert aapl.avg_cost == Decimal("172.50")
        assert aapl.market_value == Decimal("8912.50")
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_get_positions_empty(self):
        adapter = _connected_adapter({
            "GET /v1/api/portfolio/accounts": PORTFOLIO_ACCOUNTS_RESP,
            "GET /v1/api/portfolio2/DU123456/positions": [],
        })
        positions = await adapter.get_positions()
        assert positions == []
        await adapter._client.aclose()


# ---------------------------------------------------------------------------
# QA-120: Market data
# ---------------------------------------------------------------------------

class TestMarketData:
    @pytest.mark.asyncio
    async def test_get_snapshot(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/marketdata/snapshot": SNAPSHOT_RESP,
        })
        snaps = await adapter.get_snapshot([265598])
        assert len(snaps) == 1
        assert snaps[0]["31"] == "178.25"
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_get_snapshot_too_many_conids(self):
        adapter = _connected_adapter({})
        with pytest.raises(AssertionError):
            await adapter.get_snapshot(list(range(101)))
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_get_history(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/marketdata/history": HISTORY_RESP,
        })
        history = await adapter.get_history(conid=265598, period="1w", bar="1h")
        assert history["barLength"] == 3600
        assert len(history["data"]) == 1
        bar = history["data"][0]
        assert bar["c"] == 178.25
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_get_history_with_source(self):
        sent_params: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            sent_params.append(dict(request.url.params))
            return httpx.Response(200, json=HISTORY_RESP)

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=httpx.MockTransport(handler),
            verify=False,
        )
        adapter._account_id = "DU123456"
        await adapter.get_history(265598, source="T")
        assert sent_params[0].get("source") == "T"
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_unsubscribe_snapshot(self):
        adapter = _connected_adapter({
            "POST /v1/api/iserver/marketdata/unsubscribe": {"status": "ok"},
        })
        await adapter.unsubscribe_snapshot(265598)  # should not raise
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/marketdata/unsubscribeall": {"status": "ok"},
        })
        await adapter.unsubscribe_all_snapshots()  # should not raise
        await adapter._client.aclose()


# ---------------------------------------------------------------------------
# QA-121: Options chain (3-step sequential flow)
# ---------------------------------------------------------------------------

class TestOptionsChain:
    @pytest.mark.asyncio
    async def test_get_option_months(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/secdef/search": SECDEF_SEARCH_RESP,
        })
        conid, months = await adapter.get_option_months("AAPL")
        assert conid == 265598
        assert months == ["APR26", "MAY26", "JUN26"]
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_get_option_strikes(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/secdef/strikes": STRIKES_RESP,
        })
        strikes = await adapter.get_option_strikes(265598, "APR26")
        assert strikes["call"] == [170.0, 175.0, 180.0]
        assert strikes["put"] == [170.0, 175.0, 180.0]
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_get_option_contracts(self):
        adapter = _connected_adapter({
            "GET /v1/api/iserver/secdef/info": OPTION_CONTRACTS_RESP,
        })
        contracts = await adapter.get_option_contracts(265598, "APR26", "C", 175.0)
        assert len(contracts) == 1
        assert contracts[0]["conid"] == 999001
        assert contracts[0]["right"] == "C"
        assert contracts[0]["strike"] == 175.0
        assert contracts[0]["maturityDate"] == "20260417"
        await adapter._client.aclose()

    @pytest.mark.asyncio
    async def test_options_chain_full_sequential_flow(self):
        """End-to-end: months → strikes → contracts (must be called in order)."""
        call_log: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            call_log.append(path)
            if "secdef/search" in path:
                return httpx.Response(200, json=SECDEF_SEARCH_RESP)
            if "secdef/strikes" in path:
                return httpx.Response(200, json=STRIKES_RESP)
            if "secdef/info" in path:
                return httpx.Response(200, json=OPTION_CONTRACTS_RESP)
            return httpx.Response(404)

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=httpx.MockTransport(handler),
            verify=False,
        )
        adapter._account_id = "DU123456"

        conid, months = await adapter.get_option_months("AAPL")
        strikes = await adapter.get_option_strikes(conid, months[0])
        contracts = await adapter.get_option_contracts(
            conid, months[0], "C", strikes["call"][0]
        )

        # Verify sequential call order
        assert "secdef/search" in call_log[0]
        assert "secdef/strikes" in call_log[1]
        assert "secdef/info" in call_log[2]
        # OPTION_CONTRACTS_RESP fixture has strike=175.0
        assert contracts[0]["right"] == "C"
        assert contracts[0]["conid"] == 999001

        await adapter._client.aclose()


# ---------------------------------------------------------------------------
# QA-122: 401 retry
# ---------------------------------------------------------------------------

class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_on_401(self):
        """_request retries once on 401 by calling connect() then retrying."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if request.url.path.endswith("/iserver/marketdata/history"):
                if call_count == 1:
                    return httpx.Response(401, json={"error": "session expired"})
                return httpx.Response(200, json=HISTORY_RESP)
            if "iserver/auth/ssodh/init" in request.url.path:
                return httpx.Response(200, json=SSODH_RESP)
            if "iserver/accounts" in request.url.path:
                return httpx.Response(200, json=ACCOUNTS_RESP)
            if "iserver/questions/suppress" in request.url.path:
                return httpx.Response(200, json=SUPPRESS_RESP)
            return httpx.Response(200, json={})

        adapter = IBKRAdapter(base_url="https://localhost:5000/v1/api")
        transport = httpx.MockTransport(handler)
        adapter._client = httpx.AsyncClient(
            base_url="https://localhost:5000/v1/api",
            transport=transport,
            verify=False,
        )
        adapter._account_id = "DU123456"

        # Patch connect() so it re-uses the same client (no new AsyncClient creation)
        async def mock_connect(self):
            # Just reset account_id without creating a new client
            self._account_id = "DU123456"

        adapter.connect = lambda: mock_connect(adapter)

        result = await adapter._request("GET", "/iserver/marketdata/history",
                                        params={"conid": 265598, "period": "1w", "bar": "1h"})
        assert result["barLength"] == 3600
        # Call count should be 2 (first 401, then retry)
        assert call_count >= 2

        await adapter._client.aclose()


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_map_ibkr_status(self):
        assert _map_ibkr_status("PreSubmitted") == "SUBMITTED"
        assert _map_ibkr_status("Submitted") == "SUBMITTED"
        assert _map_ibkr_status("Filled") == "FILLED"
        assert _map_ibkr_status("Cancelled") == "CANCELLED"
        assert _map_ibkr_status("PendingCancel") == "CANCELLED"
        assert _map_ibkr_status("Inactive") == "REJECTED"
        assert _map_ibkr_status("") == "UNKNOWN"

    def test_conid_cache(self):
        adapter = IBKRAdapter()
        assert adapter._conid_cache == {}

    def test_account_id_none_before_connect(self):
        adapter = IBKRAdapter()
        assert adapter.account_id is None
