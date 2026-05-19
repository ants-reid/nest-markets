# IBKR Campus Action Plan — market-hunter-mvp

> Synthesized from full IBKR Campus research: API Home, REST API 2.30.0 reference,
> OpenAPI spec (`https://api.ibkr.com/gw/api/v3/api-docs`, fetched 2026-04-24),
> Order Types, Contracts, Market Data Subscriptions, Flex Web Service pages.
>
> **API Choice: IB REST API 2.30.0** (`httpx.AsyncClient`, HTTP to IB Client Portal Gateway).
> Gateway base URL (paper/local): `https://localhost:5000/v1/api`
> Gateway base URL (live/OAuth): `https://api.ibkr.com/v1/api`
> Primary file to implement: `apps/api/app/clients/broker/ibkr_adapter.py`
>
> **Decision rationale (2026-04-24):** REST API is a cleaner fit for FastAPI than TWS socket API —
> standard `httpx` async HTTP, no EWrapper/EClient inheritance, no daemon thread, no callback
> synchronization, directly composable with FastAPI dependency injection and background tasks.

---

## Table of Contents

1. [Pre-Flight Compliance & Account Setup](#1-pre-flight-compliance--account-setup)
2. [TWS / IB Gateway Configuration](#2-tws--ib-gateway-configuration)
3. [Model Gap Fixes (required before live trading)](#3-model-gap-fixes)
4. [Connection & Architecture](#4-connection--architecture)
5. [Account & Portfolio Data API](#5-account--portfolio-data-api)
6. [Order Placement & Management](#6-order-placement--management)
7. [Bracket / OCA / Stop Orders](#7-bracket--oca--stop-orders-rest-api)
8. [Positions & P&L](#8-positions--pnl)
9. [Market Data](#9-market-data)
10. [Historical Bars & Real-Time Bars](#10-historical-bars--real-time-bars)
11. [News Data](#11-news-data)
12. [Flex Web Service (Daily Reconciliation)](#12-flex-web-service-daily-reconciliation)
13. [Error Handling Reference](#13-error-handling-reference)
14. [Phased Implementation Roadmap (BP-15.XX)](#14-phased-implementation-roadmap)
15. [Market Data Subscription Checklist](#15-market-data-subscription-checklist)
16. [Algo Orders (Future Phase)](#16-algo-orders-future-phase)
17. [Options Chain Discovery](#17-options-chain-discovery)

---

## 1. Pre-Flight Compliance & Account Setup

These must be completed in Client Portal **before** any API code runs against a live account.
Paper trading does NOT require all of these but good to do early.

| Task | Where | Notes |
|------|--------|-------|
| Sign **Market Data API Acknowledgement** | Client Portal → Settings → Market Data Subscriptions | Required for all API market data |
| Sign **Automation and Software Disclosure** | Client Portal → Settings | Select **Option 3** — "Algorithmic/automated trading system" |
| Sign **API User Activity Certification** | Client Portal → Settings | Required if trading futures via API |
| Set Professional vs Non-Professional status | Client Portal → Settings → Market Data | Default is Professional; update if eligible for Non-Pro (lower fees) |
| Confirm paper trading credentials | Client Portal → Settings → Paper Trading Account | Paper account has its own username/password |

**Market Data Lines Formula:**  
`max(commissions_USD / 8, equity_USD × 100 / 1_000_000, 100)`  
Default minimum = **100 lines**. This limits concurrent subscriptions AND pacing.

---

## 2. Client Portal Gateway Setup

> **Decision:** Using IB REST API (Client Portal Gateway), not TWS socket API.

### 2.1 Download & Start Gateway
```bash
# Download Client Portal Gateway from IBKR
# https://www.interactivebrokers.com/en/trading/ib-api.php → "Client Portal Web API" section
unzip cp-api-stable.zip
cd cp-api-stable
java -jar cp-api-stable.jar root/conf.yaml
```

Gateway runs at `https://localhost:5000` (self-signed TLS cert — accept in browser or use `httpx` with `verify=False` for local dev).

### 2.2 Configuration (`root/conf.yaml`)
Key settings:
```yaml
listenPort: 5000
paperUsername: YOUR_PAPER_USERNAME
paperPassword: YOUR_PAPER_PASSWORD  # or prompt on start
```

### 2.3 Session Init Flow (local gateway)
```
POST /iserver/auth/ssodh/init   → {authenticated: true, established: true}
GET  /iserver/accounts           → required pre-flight; returns account list + selectedAccount
POST /iserver/questions/suppress → suppress all order reply prompts (automation mode)
POST /tickle                     → every 60 s to keep session alive
POST /logout                     → on shutdown
```

### 2.4 `POST /iserver/questions/suppress` — suppress all standard replies
```json
{
  "messageIds": ["o163","o354","o382","o383","o403","o451","o2136","o2137",
                 "o2165","o10082","o10138","o10151","o10152","o10153","o10164",
                 "o10223","o10288","o10331","o10332","o10333","o10334","o10335",
                 "o10336","p6","p12"]
}
```
Returns `{"status": "submitted"}`.

### 2.5 Ports Quick Reference
| Environment | Gateway Type | Port | Base URL |
|------------|-------------|------|----------|
| Paper (local) | Client Portal Gateway | 5000 | `https://localhost:5000/v1/api` |
| Live (OAuth) | IB REST API prod | 443 | `https://api.ibkr.com/v1/api` |

---

## 3. Model Gap Fixes

These DB model changes are needed to store IBKR REST API data correctly.

### 3.1 `apps/api/app/db/models/asset.py`
Add: `ibkr_con_id: int | None` — static IBKR contract ID (AAPL = 265598, EURUSD = 15016138).  
**Best practice:** Resolve via `GET /iserver/secdef/search?symbol=AAPL&secType=STK` and cache.

### 3.2 `apps/api/app/db/models/position.py`
Add fields:
- `broker_order_id: str | None` — IBKR `orderId` that created/last modified position
- `ibkr_con_id: int | None` — `conid` from positions response
- `market_value: float | None` — `marketValue` from positions response
- `commission_paid: float | None` — from trade history `commission` field

### 3.3 `apps/api/app/db/models/paper_order.py`
Add fields:
- `broker_order_id: int | None` — `order_id` from order submission response
- `commission: float | None` — from `GET /iserver/account/trades` response
- `avg_fill_price: float | None` — `average_price` from `GET /iserver/account/order/status/{orderId}`
- `ibkr_status: str | None` — raw IBKR status string (PreSubmitted/Submitted/Filled/Cancelled/PendingCancel)

### 3.4 `apps/api/app/clients/broker/broker_interface.py` (Protocol)
Gaps in `AccountInfo`:
- Add `excess_liquidity: float`
- Add `margin: float` (maps to `maintenanceMargin` in summary response)
- Add `unrealized_pnl: float`

Add method: `get_positions() -> list[PositionInfo]`

---

## 4. Connection & Architecture (REST API)

### 4.1 REST API Architecture

```python
import httpx
from contextlib import asynccontextmanager

class IBKRAdapter:
    def __init__(self, base_url: str = "https://localhost:5000/v1/api"):
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._account_id: str | None = None

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(base_url=self._base_url, verify=False)
        await self._client.post("/iserver/auth/ssodh/init",
                                json={"compete": False, "publish": True})
        resp = await self._client.get("/iserver/accounts")
        self._account_id = resp.json()["selectedAccount"]
        await self._suppress_order_replies()

    async def tickle(self) -> None:
        """Call every 60 s to keep session alive."""
        await self._client.post("/tickle")

    async def disconnect(self) -> None:
        await self._client.post("/logout")
        await self._client.aclose()
```

### 4.2 FastAPI background keep-alive task
```python
# In FastAPI lifespan or startup event
import asyncio
async def tickle_loop(adapter: IBKRAdapter):
    while True:
        await asyncio.sleep(60)
        await adapter.tickle()

# Start as background task
asyncio.create_task(tickle_loop(adapter))
```

### 4.3 Contract lookup (`GET /iserver/secdef/search`)
```python
async def resolve_conid(self, symbol: str, sec_type: str = "STK") -> int:
    resp = await self._client.get(
        "/iserver/secdef/search",
        params={"symbol": symbol, "secType": sec_type}
    )
    results = resp.json()
    return results[0]["conid"]  # first match for standard equities
```

### 4.4 Session token / OAuth (live production)
For live: OAuth 1.0a flow:
1. `POST /oauth/request_token` → temp token
2. User authorizes at IBKR portal
3. `POST /oauth/access_token` → access token
4. `POST /oauth/live_session_token` → Live Session Token (LST)
5. `POST /iserver/auth/ssodh/init` → initialize session

For paper/local gateway: username/password via browser login at `https://localhost:5000` (no OAuth needed).

---

## 5. Account & Portfolio Data API

### 5.1 Account Summary (`GET /iserver/account/{accountId}/summary`)
Returns overview of account balance values.
```python
resp = await client.get(f"/iserver/account/{account_id}/summary")
data = resp.json()
# Fields: netLiquidationValue, totalCashValue, buyingPower,
#         availableFunds, excessLiquidity, initialMargin, maintenanceMargin
```

Also available:
- `GET /iserver/account/{accountId}/summary/balances` — breakdown by segment
- `GET /iserver/account/{accountId}/summary/margins` — margin detail
- `GET /iserver/account/{accountId}/summary/available_funds` — available funds detail

### 5.2 P&L (`GET /iserver/account/pnl/partitioned`)
```python
resp = await client.get("/iserver/account/pnl/partitioned")
upnl = resp.json()["upnl"]  # keyed by "{accountId}.Core"
core = upnl.get(f"{account_id}.Core", {})
# core.dpl = daily P&L, core.upl = unrealized P&L, core.nl = net liq
```
Note: initial request may return empty `upnl` — poll once after 1 s.

### 5.3 Portfolio ledger (`GET /portfolio/{accountId}/ledger`)
Returns per-currency cash balances, settled cash, interest, market values by asset class.

---

## 6. Order Placement & Management

### 6.1 Submit an Order (`POST /iserver/account/{accountId}/orders`)
```python
# Body is a plain JSON array (NOT wrapped in {"orders": [...]})
order_body = [{
    "conid": 265598,           # AAPL
    "orderType": "LMT",        # MKT, LMT, STP, STP LMT, TRAIL, TRAIL LIMIT
    "side": "BUY",             # BUY or SELL
    "quantity": 100,
    "price": 250.00,           # limit price (LMT orders)
    "tif": "DAY",              # DAY, GTC, IOC, GTD
    "outsideRTH": False,
    "cOID": "my-order-123",    # client-configurable ID for tracking
    # "cashQty": 500.00,         # alternative to quantity: submit dollar value (Stocks/Crypto/Forex; Mar 2026)
    # "manualIndicator": False,  # REQUIRED for US Futures orders (CME Rule 536-B, May 2025+)
}]
resp = await client.post(f"/iserver/account/{account_id}/orders", json=order_body)
```

Response is one of:
- `orderSubmitSuccess`: `[{"order_id": 1234, "order_status": "PreSubmitted", ...}]`
- `orderReplyMessage`: `[{"id": "replyId", "message": ["Price pct...", "..."], ...}]` → requires confirm
- `orderSubmitError`: `{"error": "..."}`

### 6.2 Handle order reply (if not suppressed)
```python
if "id" in response[0]:  # orderReplyMessage
    reply_id = response[0]["id"]
    await client.post(f"/iserver/reply/{reply_id}", json={"confirmed": True})
```

### 6.3 Order status polling (`GET /iserver/account/order/status/{orderId}`)
```python
resp = await client.get(f"/iserver/account/order/status/{order_id}")
status = resp.json()
# status.order_status: PreSubmitted → Submitted → Filled / Cancelled / PendingCancel
# status.average_price, status.cum_fill, status.remaining_quantity
```

### 6.4 Order Management
```python
# Open orders
resp = await client.get("/iserver/account/orders")
orders = resp.json()["orders"]

# Cancel order
resp = await client.delete(f"/iserver/account/{account_id}/order/{order_id}")

# Cancel all open orders
resp = await client.delete(f"/iserver/account/{account_id}/orders")

# Trade history (completed/filled)
resp = await client.get("/iserver/account/trades")
trades = resp.json()  # list of fills with conid, execution_id, price, size, side
```

### 6.5 Modify an Order (`POST /iserver/account/{accountId}/order/{orderId}`)
Must include **ALL original order fields** in the POST body — not just the changed field. Partial updates are rejected. Cannot change `side` or `orderType` — cancel and re-place instead.

### 6.6 WhatIf Orders (`POST /iserver/account/{accountId}/orders/whatif`)
Same body as order submission. Returns `orderPreview` with projected margin impact.

### 6.7 Order Status Values Reference
| Status | Meaning |
|--------|---------|
| `PreSubmitted` | Received by gateway, not yet at exchange |
| `Submitted` | Active at exchange |
| `Filled` | Fully executed |
| `Cancelled` | Cancelled |
| `PendingCancel` | Cancel in progress |
| `Inactive` | Rejected or expired |

---

## 7. Bracket / OCA / Stop Orders (REST API)

### 7.1 Bracket Orders (array submission)
Submit all three orders in a single `POST /iserver/account/{accountId}/orders` call.
Use `cOID` on parent and `parentId` on children equal to parent's `cOID`.

```python
import uuid
parent_coid = f"bracket-{uuid.uuid4()}"
# Body is a plain JSON array — all three orders in one POST
body = [
    {
        "conid": 265598, "orderType": "LMT", "side": "BUY",
        "quantity": 100, "price": 250.00, "tif": "DAY",
        "cOID": parent_coid,
    },
    {
        "conid": 265598, "orderType": "LMT", "side": "SELL",
        "quantity": 100, "price": 260.00, "tif": "GTC",
        "parentId": parent_coid,
    },
    {
        "conid": 265598, "orderType": "STP", "side": "SELL",
        "quantity": 100, "auxPrice": 240.00, "tif": "GTC",
        "parentId": parent_coid,
    },
]
resp = await client.post(f"/iserver/account/{account_id}/orders", json=body)
```

### 7.2 OCA (One-Cancels-All) Orders
Submit all orders in a **single** `POST /iserver/account/{accountId}/orders` call with `isSingleGroup: true` on every order in the group.
All orders in the group will share the same `oca_group_id` (visible only after submission via `/iserver/account/order/status/{orderId}`).

```python
import uuid
coid_a = f"oca-a-{uuid.uuid4()}"
coid_b = f"oca-b-{uuid.uuid4()}"
body = [
    {
        "conid": 265598, "secType": "265598:STK",
        "cOID": coid_a, "orderType": "LMT",
        "side": "BUY", "quantity": 1, "price": 145.25,
        "tif": "DAY", "isSingleGroup": True,
    },
    {
        "conid": 8314, "secType": "8314:STK",
        "cOID": coid_b, "orderType": "LMT",
        "side": "BUY", "quantity": 1, "price": 125.50,
        "tif": "DAY", "isSingleGroup": True,
    },
]
resp = await client.post(f"/iserver/account/{account_id}/orders", json=body)
# Response: [{"order_id": "...", "order_status": "PreSubmitted", ...}, {...}]
# Then fetch oca_group_id:
status = await client.get(f"/iserver/account/order/status/{resp.json()[0]['order_id']}")
oca_group_id = status.json()["oca_group_id"]  # e.g. "oco-1297028125"
```

### 7.3 Stop and Trailing Stop (REST field mapping)
| Order Type | `orderType` | Price fields |
|------------|-------------|-------------|
| Stop Market | `"STP"` | `auxPrice` = stop trigger |
| Stop Limit | `"STP LMT"` | `price` = limit, `auxPrice` = stop |
| Trailing Stop $ | `"TRAIL"` | `trailingAmt`, `trailingType="amt"` |
| Trailing Stop % | `"TRAIL"` | `trailingAmt`, `trailingType="%"` |

### 7.4 Available order types per contract
Check with `POST /iserver/contract/rules` body `{"conid": 265598, "isBuy": true}`.
Response `orderTypes` lists valid REST order type strings.

---

## 8. Positions & P&L

### 8.1 Request Positions (`GET /portfolio2/{accountId}/positions`)
Real-time positions, no cache.
```python
resp = await client.get(f"/portfolio2/{account_id}/positions")
positions = resp.json()
# Each: conid, position, marketPrice, marketValue, avgCost, avgPrice,
#       realizedPnl, unrealizedPnl, assetClass, ticker
```
Requires `GET /portfolio/accounts` pre-flight (loads account data into gateway cache).

### 8.2 P&L (`GET /iserver/account/pnl/partitioned`)
```python
resp = await client.get("/iserver/account/pnl/partitioned")
upnl = resp.json()["upnl"]
core = upnl.get(f"{account_id}.Core", {})
# core.dpl = daily P&L, core.upl = unrealized P&L, core.nl = net liq
```
Note: initial request may return empty — poll once after 1 s.

---

## 9. Market Data

### 9.1 Snapshot Polling (`GET /iserver/marketdata/snapshot`)
REST API uses polling rather than streaming. First call is a subscription and may return empty — poll again after 1–2 s.

```python
FIELD_CODES = "31,84,85,86,87,7295,7296,70,71"
# 31=last, 84=bid, 86=ask, 85=bidSize, 87=askSize, 7295=open, 7296=close, 70=high, 71=low
# New (Mar 2026): 6508=Stock Type (e.g. "COMMON"), 6509=Option Right ("C" or "P")

resp = await client.get(
    "/iserver/marketdata/snapshot",
    params={"conids": conid, "fields": FIELD_CODES}
)
data = resp.json()[0]  # list, one entry per conid
last_price = data.get("31")
bid = data.get("84")
ask = data.get("86")
```

> **Limits (Dec 2025):** Maximum 100 `conids` per query and 50 fields at a time.

### 9.2 Unsubscribe
```python
# Unsubscribe one contract
await client.post("/iserver/marketdata/unsubscribe", json={"conid": str(conid)})

# Unsubscribe all
await client.get("/iserver/marketdata/unsubscribeall")
```

### 9.3 WebSocket Streaming (alternative to snapshot polling)
WebSocket endpoint: `wss://localhost:5000/v1/api/ws` (paper/local)

**Connection + authentication handshake:**
```python
# After ws.connect(), the server sends: {"message": "waiting for session"}
# Fetch session value from /tickle, then send:
await ws.send(json.dumps({"session": tickle_resp["session"]}))
# Server confirms:
# {"topic": "sts", "args": {"authenticated": true}}
# {"topic": "system", "success": "<username>"}
```

```
# Subscribe to top-of-book for a contract
smd+{conid}+{"fields":["31","84","85","86","87","88"]}
# 31=last, 84=bid, 85=bidSize, 86=ask, 87=askSize, 88=lastTimestamp

# Unsubscribe
umd+{conid}+{}

# PnL stream (note: returns "uel" field, not "el")
spl+{}

# Order updates stream — filter by status (Aug 2025+)
# Valid filter values: PreSubmitted, Submitted, Filled, Cancelled, WarnState, etc.
sor+{"filters":["Filled"]}   # e.g. receive only Filled events
sor+{}                       # no filter — receive all order status changes
```

> **CRITICAL (Apr 2026):** WebSocket `smd` subscriptions **auto-terminate after 10 minutes**.
> Implement a resubscription timer — send a new `smd+{conid}+{...}` before the 10-minute mark.

```python
import asyncio, websockets, json

async def stream_market_data(conid: int, fields: list[str]):
    uri = "wss://localhost:5000/v1/api/ws"
    subscribe_msg = f"smd+{conid}+{{\"fields\":{json.dumps(fields)}}}"
    async with websockets.connect(uri, ssl=False) as ws:
        await ws.send(subscribe_msg)
        resub_at = asyncio.get_event_loop().time() + 570  # resubscribe at 9m30s
        async for message in ws:
            data = json.loads(message)
            yield data
            if asyncio.get_event_loop().time() >= resub_at:
                await ws.send(subscribe_msg)  # resubscribe before 10-min cutoff
                resub_at = asyncio.get_event_loop().time() + 570
```

### 9.4 API Pacing Limits

| Endpoint / Scope | Limit |
|-----------------|-------|
| **Global** | 10 req/s per session |
| `/iserver/marketdata/snapshot` | 10 req/s; max 100 conids, 50 fields per call |
| `/iserver/account/orders` (GET) | 1 req / 5 s |
| `/iserver/account/pnl/partitioned` | 1 req / 5 s |
| `/portfolio/accounts` | 1 req / 5 s |
| `/iserver/marketdata/history` | 5 concurrent requests max |
| **429 response** | IP penalty box — **10-minute lockout** |

> **Strategy:** Use a token-bucket or simple `asyncio.sleep` between rapid calls. The 429 penalty (10 minutes) is severe — never burst historical data requests.

---

## 10. Historical Bars

### 10.1 Historical Data Request (`GET /iserver/marketdata/history`)
```python
resp = await client.get(
    "/iserver/marketdata/history",
    params={
        "conid": 265598,       # AAPL
        "period": "1w",        # 1d, 1w, 1m, 3m, 1y
        "bar": "1h",           # 1min, 5min, 1h, 1d, 1w
        "outsideRth": False,
        "startTime": "",       # optional: "YYYYMMDD-HH:mm:ss"
        # "source": "T",       # optional (Feb 2026+): T=trades, B=bid, A=ask, M=midpoint
    }
)
history = resp.json()
# history.barLength (seconds per bar)
# history.data: [{o, h, l, c, v, t}] — t is Unix timestamp ms
```

**`whatToShow` (optional param)**:
| Value | Description |
|-------|-------------|
| `Last` | Trade prices (default) |
| `Midpoint` | Midpoint prices |
| `Bid` | Bid prices |
| `Ask` | Ask prices |

---

## 11. News Data

News via `reqMktData` genericTick 292 is TWS-API specific and **does not apply to the REST API**.

For REST-based news alternatives:
- **FYI Notifications**: `GET /fyi/notifications` — IBKR alert/notification system
- **Flex Web Service**: End-of-day news-related flex reports (see §12)
- **Third-party news APIs**: Benzinga, Polygon.io, etc. — integrate directly via HTTP

---

## 12. Flex Web Service (Daily Reconciliation)

Use Flex Web Service for **end-of-day reconciliation** of trades, positions, and P&L.  
Not suitable for real-time (data updates once daily at market close; trade confirmations within 5-10 min).

### 12.1 Setup (One-Time in Client Portal)
1. `Reporting → Flex Queries → Flex Web Service Configuration`
2. Enable Flex Web Service → copy **Current Token** (store securely, not in code)
3. Create an **Activity Flex Query** → capture **Query ID**
4. Create a **Trade Confirmation Flex Query** → capture **Query ID**

Token validity: 6 hours to 1 year (configurable). Can restrict by IP.

### 12.2 Two-Step Request Pattern
```python
import requests, time, xml.etree.ElementTree as ET

BASE = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
TOKEN = os.environ["FLEX_TOKEN"]   # never hardcode
QUERY_ID = os.environ["FLEX_QUERY_ID"]

# Step 1: Generate report
resp = requests.get(f"{BASE}/SendRequest",
                    params={"t": TOKEN, "q": QUERY_ID, "v": 3},
                    headers={"User-Agent": "market-hunter-mvp/1.0"})
root = ET.fromstring(resp.text)
ref_code = root.find("ReferenceCode").text
status = root.find("Status").text
assert status == "Success", f"Flex report generation failed: {root.find('ErrorMessage').text}"

# Step 2: Retrieve report (wait for generation — large reports may need longer)
time.sleep(20)
resp2 = requests.get(f"{BASE}/GetStatement",
                     params={"t": TOKEN, "q": ref_code, "v": 3},
                     headers={"User-Agent": "market-hunter-mvp/1.0"})
# resp2.text contains full XML/CSV report
```

### 12.3 Rate Limits
- Max 1 request/second, 10 requests/minute per token
- Error 1019: "Statement generation in progress" — retry after delay

### 12.4 Recommended Use Cases
- Morning reconciliation: import prior-day fills into DB
- Position verification: compare DB positions vs IBKR activity statement
- Commission tracking: reconcile commission totals against DB

---

## 13. Error Handling Reference

### 13.1 HTTP Status Codes
| Status | Meaning | Action |
|--------|---------|--------|
| 200 | OK | Success |
| 400 | Bad Request | Check request body / params |
| 401 | Unauthorized — session expired | Re-run `POST /iserver/auth/ssodh/init` + `GET /iserver/accounts` |
| 404 | Not Found | Check endpoint URL or orderId |
| 500 | Internal Server Error | Retry; check gateway logs |
| 503 | Service Unavailable — gateway busy | Back off and retry |

### 13.2 Session Expiry Pattern
```python
async def _request_with_retry(self, method: str, path: str, **kwargs):
    resp = await self._client.request(method, path, **kwargs)
    if resp.status_code == 401:
        await self.connect()  # re-auth and refresh session
        resp = await self._client.request(method, path, **kwargs)
    resp.raise_for_status()
    return resp
```

### 13.3 Gateway Startup Errors
- **Connection refused on port 5000**: Gateway not started — run `java -jar cp-api-stable.jar` first.
- **SSL certificate error**: Use `verify=False` in `httpx.AsyncClient` for local dev (self-signed cert).
- **Empty response from `/iserver/accounts`**: Session not authenticated — log in at `https://localhost:5000` in browser first.

### 13.4 Order Placement Errors
| Error | Meaning | Action |
|-------|---------|--------|
| `orderSubmitError` with "price out of range" | Limit too far from market | Verify price vs current bid/ask |
| `orderReplyMessage` not suppressed | Order reply prompt | Call `POST /iserver/questions/suppress` at session start |
| 400 on order submit | Bad order body | Check required fields: `conid`, `orderType`, `side`, `quantity`, `tif` |
| 400 on futures order modify/cancel | Missing `manualIndicator` | Include `"manualIndicator": false` for automated systems (required May 2025+) |

### 13.5 Scheduled Maintenance Windows
`/iserver` endpoints go **offline daily** at 01:00 local time during server reset.

| Region | Maintenance window |
|--------|-------------------|
| North America (paper + most US accounts) | 01:00 US/Eastern |
| Europe | 01:00 CEST |
| Asia | 01:00 HKT |

Also: **Weekly reauthentication** cycle starts every Monday — if you see `Soft token=0` errors, a manual re-login is required to complete the weekly auth challenge.

```python
# Recommended: detect maintenance window and pause operations
from datetime import datetime, time
import zoneinfo

def is_maintenance_window(tz: str = "US/Eastern") -> bool:
    """Returns True during the ~5-minute /iserver maintenance window."""
    now = datetime.now(zoneinfo.ZoneInfo(tz))
    # Maintenance is ~01:00–01:05 local time
    return time(1, 0) <= now.time() <= time(1, 5)
```

---

## 14. Phased Implementation Roadmap

> See `docs/build-plan.md` Section 12 for the authoritative BP-15.XX step-by-step roadmap (fully updated for IB REST API 2.30.0).

Summary of phases:

| Phase | Focus | Key Steps |
|-------|-------|-----------|
| P0 | Infrastructure | BP-15.00–15.04: Gateway setup, `IBKRAdapter` with `httpx`, session init, model gaps |
| P1 | Core Trading | BP-15.10–15.15: Contract lookup, account info, order placement, status polling, positions |
| P2 | Risk Management | BP-15.20–15.24: Bracket orders, stop/trail, commission tracking, what-if |
| P3 | Market Data | BP-15.30–15.34: Historical bars, snapshot polling, P&L, subscriptions |
| P4 | Advanced | BP-15.40–15.42: Algo orders, cancel/modify, Flex reconciliation |

---

## 15. Market Data Subscription Checklist

Complete in **Client Portal → Settings → Market Data Subscriptions** (under the specific API username).

### Minimum for US Equity Trading
| Subscription | Approx Cost/Mo | Covers |
|-------------|---------------|--------|
| NYSE (Network A/CTA) | ~$15 non-pro | NYSE-listed stocks |
| Network B (ARCA/BATS/IEX) | ~$15 non-pro | ARCA, BATS, IEX (SPY, VXX, ETFs) |
| NASDAQ (Network C/UTP) | ~$15 non-pro | AAPL, MSFT, TSLA, most tech |

**OR** use the bundle:
- **US Equity and Options Add-On Streaming Bundle** — all three + OPRA (all US options) in one package

REST snapshot API uses polling. A valid market data subscription is still required to receive live quotes.

### Important Notes
- Subscriptions are **per username** — paper account needs its own separate subscriptions
- Non-professional designation required for lower rates (must verify eligibility)

---

## 16. Algo Orders (Future Phase — BP-15.40)

All IB Algorithms are **regular trading hours only** (`outsideRth` must be `false`).

### Check available algos (`GET /iserver/contract/{conid}/algos`)
```python
resp = await client.get(
    f"/iserver/contract/{conid}/algos",
    params={"algos": "Adaptive;Vwap;Twap", "addParams": "1"}
)
algos = resp.json()  # list of available algo strategies with parameter schemas
```

> **Format note:** The 2021 tutorial articles show `strategy` + `strategyParameters: {key: value}` (flat object).
> The current REST API spec (2.30.0) uses `algoStrategy` + `algoParams: [{"tag": ..., "value": ...}]` (array of tag/value pairs).
> Use the current spec format below.

### Adaptive Algo (simplest — good default)
```python
# Body is a plain JSON array
order_body = [{
    "conid": 265598,
    "orderType": "LMT",
    "side": "BUY",
    "quantity": 1000,
    "price": 250.00,
    "tif": "DAY",
    "useAdaptive": True,           # triggers Adaptive algo
    "adaptivePriority": "Normal",  # Patient, Normal, or Urgent
}]
```

### VWAP / TWAP (via algoStrategy fields)
```python
# Body is a plain JSON array
order_body = [{
    "conid": 265598,
    "orderType": "LMT",
    "side": "BUY",
    "quantity": 1000,
    "tif": "DAY",
    "algoStrategy": "Vwap",
    "algoParams": [
        {"tag": "startTime", "value": "09:30:00 US/Eastern"},
        {"tag": "endTime", "value": "16:00:00 US/Eastern"},
        {"tag": "maxPctVol", "value": "0.1"},
    ]
}]
```

### Algo Strategy — When to Use
| Strategy | Use Case |
|---------|---------|
| Adaptive (Normal) | Standard-size orders, any time |
| VWAP | Large orders, match market volume |
| TWAP | Large orders, minimize market impact |


---

## 17. Options Chain Discovery

Three-step sequential flow — each step depends on the previous response.

### 17.1 Step 1 — Underlying contract + available months
```python
# GET /iserver/secdef/search?symbol=AAPL → returns sections[].months for OPT
resp = await client.get("/iserver/secdef/search", params={"symbol": "AAPL"})
for contract in resp.json():
    if contract["description"] == "NASDAQ":  # filter by listing exchange
        under_conid = contract["conid"]
        for sec in contract["sections"]:
            if sec["secType"] == "OPT":
                months = sec["months"].split(";")  # e.g. ["APR26", "MAY26", ...]
front_month = months[0]
```

### 17.2 Step 2 — Strikes for a month
```python
# Returns {"call": [145.0, 150.0, ...], "put": [145.0, 150.0, ...]}
resp = await client.get(
    "/iserver/secdef/strikes",
    params={"conid": under_conid, "sectype": "OPT", "month": front_month, "exchange": "SMART"}
)
strikes = resp.json()["put"]  # put and call lists usually match; use put as base
```

### 17.3 Step 3 — Contract details per strike
```python
# Returns all expiry variants for the given month+strike (including weeklies)
resp = await client.get(
    "/iserver/secdef/info",
    params={
        "conid": under_conid, "sectype": "OPT",
        "month": front_month, "right": "C",    # C=Call, P=Put
        "exchange": "SMART", "strike": 150.0
    }
)
for contract in resp.json():
    # contract.conid, contract.symbol, contract.right,
    # contract.strike, contract.maturityDate (YYYYMMDD),
    # contract.multiplier, contract.tradingClass, contract.currency
    pass
```

### 17.4 Derivatives contract lookup (Futures, Warrants)
Same 3-step flow with `sectype` = `FUT` (no `right` or `strike` needed for futures).
`/iserver/secdef/search` response also includes `fop` (Futures Options expiries) and `war` (Warrants).

---

## Quick Reference: Contract / conId Lookup (REST API)

Use `GET /iserver/secdef/search` to resolve a symbol to a `conid`.

```python
# Search by symbol
resp = await client.get("/iserver/secdef/search", params={"symbol": "AAPL", "secType": "STK"})
conid = resp.json()[0]["conid"]  # 265598 for AAPL

# Get full contract details
resp = await client.get("/iserver/secdef/info", params={"conid": 265598, "secType": "STK"})
info = resp.json()[0]
# info.conid, info.symbol, info.companyName, info.exchange, info.currency

# Check valid order types for a contract
resp = await client.post("/iserver/contract/rules", json={"conid": 265598, "isBuy": True})
order_types = resp.json()["orderTypes"]  # list of valid REST orderType strings
```

**Known conIds** (static, do not change):
- AAPL = 265598 (NASDAQ/ISLAND)
- SPY = 756733 (ARCA)

---

*Last updated from IBKR Campus research session. Reference: `docs/ibkr-api-knowledge-bank.md` for TWS API fundamentals.*
