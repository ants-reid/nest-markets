# IBKR API Knowledge Bank

**Created:** 2026  
**Source:** IBKR Campus TWS API Documentation — https://ibkrcampus.com/campus/ibkr-api-page/trader-workstation-api/  
**Purpose:** Cross-reference IBKR API capabilities with existing codebase; identify gaps and maximisation opportunities for Phase 15 broker integration.

---

## 1. API Options Comparison

| Feature | TWS API | Web API (Client Portal) |
|---|---|---|
| Protocol | TCP Socket (EClient/EWrapper) | REST/WebSocket HTTPS |
| Authentication | TWS/IB Gateway running locally | OAuth / API Key |
| Real-time streaming | ✅ Native streaming | ✅ WebSocket |
| Tick-by-tick data | ✅ Yes | Limited |
| L2 Market Depth | ✅ Yes | ❌ No |
| Paper trading | ✅ Port 7497 | ✅ Sandbox |
| Python package | `ibapi` (official) | HTTP client (requests/aiohttp) |
| Max connections | 32 simultaneous | Per-account rate limits |
| Mac/Linux support | ✅ Full (Python/Java/C++) | ✅ Full |
| Synchronous wrapper | ✅ New in v10.40 (`TWSSyncWrapper`) | N/A |
| Order types | All (market, limit, stop, bracket, algo, combo) | Standard only |
| Corporate events | ✅ Wall Street Horizon | ❌ No |
| Market scanner | ✅ Yes | ❌ No |
| Options Greeks | ✅ Live calculation | Limited |

**Recommendation for this project: TWS API** — the `ibkr_adapter.py` scaffold already uses `host/port/client_id` (TWS pattern). The TWS API provides richer data (L2, tick-by-tick, real-time bars, options Greeks), supports paper trading on port 7497, and fits the algorithmic trading use-case.

---

## 2. Connection Architecture

### Ports (already in scaffold — `IBKRAdapter.__init__` defaults `port=7497`)
| Mode | Software | Port |
|---|---|---|
| Paper trading | TWS | **7497** |
| Live trading | TWS | 7496 |
| Paper trading | IB Gateway | 4002 |
| Live trading | IB Gateway | 4001 |

### Python Connection Pattern
```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading

class IBKRApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: int):
        # Connection confirmed — safe to send requests
        self.next_order_id = orderId

app = IBKRApp()
app.connect("127.0.0.1", 7497, clientId=1)  # paper
thread = threading.Thread(target=app.run, daemon=True)
thread.start()
```

### Synchronous Wrapper (v10.40+) — simpler for `IBKRAdapter`
```python
from ibapi.sync_wrapper import TWSSyncWrapper

app = TWSSyncWrapper(timeout=30)
if not app.connect_and_start("127.0.0.1", port=7497, client_id=1):
    raise ConnectionError("TWS not reachable")
```

### Key connection facts
- `nextValidId` callback = connection is ready; **do not send requests before this fires**
- Up to 32 API clients per TWS session (use distinct `clientId`)
- `clientId=0` = sees all orders including manual TWS orders
- TWS must have "Enable ActiveX and Socket Clients" enabled, "Read-Only API" disabled

---

## 3. Available Data Inventory

### 3.1 Real-Time Market Data (L1)
Function: `EClient.reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, [])`  
Response callbacks: `EWrapper.tickPrice`, `EWrapper.tickSize`, `EWrapper.tickString`, `EWrapper.tickGeneric`

**Default tick types (no subscription needed):**
| Tick | ID | Description |
|---|---|---|
| `BID_SIZE` | 0 | Number of contracts at bid |
| `BID` | 1 | Bid price |
| `ASK` | 2 | Ask price |
| `ASK_SIZE` | 3 | Number of contracts at ask |
| `LAST` | 4 | Last traded price |
| `LAST_SIZE` | 5 | Last traded size |
| `HIGH` | 6 | Day high |
| `LOW` | 7 | Day low |
| `VOLUME` | 8 | Day volume |
| `CLOSE` | 9 | Previous close |
| `OPEN` | 14 | Current session open |
| `HALTED` | 49 | Whether contract is halted |

**Generic ticks (add to `genericTickList` string):**
| Generic Tick ID | Data |
|---|---|
| `104` | Historical volatility (30-day) |
| `106` | Option implied volatility |
| `165` | 13/26/52-week high/low, avg volume |
| `225` | Auction volume / imbalance |
| `232` | Mark price |
| `233` | RT Volume (time & sales) |
| `236` | Shortable / shortable shares |
| `293` | Trade count per day |
| `294` | Trade rate per minute |
| `295` | Volume rate per minute |
| `375` | RT Trade Volume (excludes unreportable) |
| `595` | Short-term volume (1/2/3/5/10 min) |
| `577` | ETF NAV last price |

**Cross-reference:** These fields are missing from the existing `quote.py` model and `market_data.py` route. Currently only OHLCV is stored in `Bar`. Adding `mark_price`, `implied_volatility`, `historical_volatility`, `shortable`, `rt_volume` would significantly enrich signal features.

### 3.2 Tick-by-Tick Data (True T&S)
Function: `EClient.reqTickByTickData(reqId, contract, tickType, numberOfTicks, ignoreSize)`  
`tickType`: `"Last"`, `"AllLast"`, `"BidAsk"`, `"MidPoint"`  
Limit: 5% of total market data lines (default = 5 subscriptions for 100 lines)

**Use for:** High-frequency signal refinement, precise entry timing, spread monitoring.

### 3.3 Historical Bars
Function: `EClient.reqHistoricalData(reqId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, [])`

**whatToShow options relevant to this project:**
| Value | Maps To |
|---|---|
| `TRADES` | Standard OHLCV → existing `Bar` model |
| `MIDPOINT` | Mid OHLCV (better for illiquid) |
| `BID_ASK` | Bid/Ask OHLCV |
| `HISTORICAL_VOLATILITY` | 30-day HV → `volatility.py` indicator |
| `OPTION_IMPLIED_VOLATILITY` | IV surface data |
| `ADJUSTED_LAST` | Corporate-action-adjusted close |

**Bar sizes available:** `1 secs`, `5 secs`, `10 secs`, `15 secs`, `30 secs`, `1 min`, `2 mins`, `3 mins`, `5 mins`, `10 mins`, `15 mins`, `20 mins`, `30 mins`, `1 hour`, `2 hours`, `3 hours`, `4 hours`, `8 hours`, `1 day`, `1 week`, `1 month`

**Cross-reference:** Existing `Bar` model stores `open/high/low/close/volume/vwap/source`. IBKR bars also have `barCount` (number of trades) and `WAP` (weighted average price ≈ VWAP). The `vwap` field already exists in `Bar` and should be populated from `bar.WAP`.

### 3.4 Real-Time 5-Second Bars
Function: `EClient.reqRealTimeBars(reqId, contract, 5, "TRADES", useRTH, [])`  
Response: `EWrapper.realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)`

**Use for:** Live candlestick construction, intraday signal updates.

### 3.5 L2 Market Depth (Order Book)
Function: `EClient.reqMktDepth(reqId, contract, numRows, isSmartDepth, [])`  
Response: `EWrapper.updateMktDepth(tickerId, position, operation, side, price, size)`  
(operation: 0=insert, 1=update, 2=delete)

**Use for:** Liquidity analysis (existing `liquidity.py` indicator), spread monitoring, order book imbalance signals.

### 3.6 Historical Time & Sales
Function: `EClient.reqHistoricalTicks(reqId, contract, startDateTime, endDateTime, numberOfTicks, whatToShow, useRth, ignoreSize, [])`  
`whatToShow`: `MIDPOINT`, `BID_ASK`, `TRADES`

### 3.7 Market Scanner
Function: `EClient.reqScannerSubscription(reqId, subscription, [], [])`  
Returns list of contracts matching scan criteria. Use `reqScannerParameters()` to get all XML-formatted filter options.

**Use for:** Universe discovery, opportunity identification — complement to existing `opportunity_ranker_service.py`.

---

## 4. Account & Portfolio Data

### 4.1 Account Summary
Function: `EClient.reqAccountSummary(reqId, "All", AccountSummaryTags.AllTags)`  
Updates every 3 minutes.

**Key tags that map to existing `AccountInfo` in `BrokerInterface`:**
| IBKR Tag | Maps To |
|---|---|
| `NetLiquidation` | `AccountInfo.net_liquidation` |
| `TotalCashValue` | `AccountInfo.cash_balance` |
| `BuyingPower` | `AccountInfo.buying_power` |
| `ExcessLiquidity` | Risk management gate |
| `MaintMarginReq` | Risk pre-flight check |
| `InitMarginReq` | Pre-trade margin check |
| `UnrealizedPnL` | `PnlSnapshot.open_pnl` |
| `RealizedPnL` | `PnlSnapshot.closed_pnl` |
| `GrossPositionValue` | `PnlSnapshot.gross_exposure` |

**Gap:** `AccountInfo` in `broker_interface.py` only has `net_liquidation`, `cash_balance`, `buying_power`. Missing: `excess_liquidity`, `margin_requirements`, `unrealized_pnl`, `realized_pnl`. These are needed by `execution_safety_gate.py` (Phase 15.2).

### 4.2 Position Updates
Function: `EClient.reqPositions()` → continuous subscription  
Response: `EWrapper.position(account, contract, position, avgCost)`  
Response: `EWrapper.updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)`

**Cross-reference with `Position` model:**
| IBKR Field | `Position` Column | Status |
|---|---|---|
| `contract.symbol` | via `asset_id → Asset.ticker` | ✅ Covered |
| `position` (qty) | `qty` | ✅ Covered |
| `avgCost` | `avg_entry_price` | ✅ Covered |
| `marketPrice` | `current_price` | ✅ Covered |
| `unrealizedPNL` | `unrealized_pnl` | ✅ Covered |
| `realizedPNL` | `realized_pnl` | ✅ Covered |
| `contract.conId` | ❌ Missing | **GAP** — add `broker_contract_id` |
| `marketValue` | ❌ Missing | **GAP** — useful for exposure calc |

### 4.3 Real-Time P&L
Function: `EClient.reqPnLSingle(reqId, account, "", conId)` — updates ~1/second  
Response: `EWrapper.pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)`

Function: `EClient.reqPnL(reqId, account, "")` — account-level  
Response: `EWrapper.pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)`

**Cross-reference:** `PnlSnapshot` stores `open_pnl` and `closed_pnl`. The `ibkr_position_monitor.py` worker (Phase 15 deliverable) should call `reqPnL` and write snapshots to `pnl_snapshots` table. Current `pnl_service.py` generates snapshots from paper fills — this pattern should be replicated for live data.

---

## 5. Order Management

### 5.1 Placing Orders
Function: `EClient.placeOrder(orderId, contract, order)`  
`orderId` must be unique and ≥ `nextValidId`

**Order object required fields:**
```python
order = Order()
order.action = "BUY"        # or "SELL"
order.orderType = "LMT"     # MKT, LMT, STP, STP LMT, TRAIL, etc.
order.totalQuantity = 100
order.lmtPrice = 250.00     # for LMT orders
order.tif = "DAY"           # DAY, GTC, IOC, GTD
```

**Cross-reference with `OrderRequest` in `broker_interface.py`:**
| `OrderRequest` Field | IBKR `Order` Field | Notes |
|---|---|---|
| `ticker` | `contract.symbol` | Need to resolve to `Contract` object |
| `side` | `order.action` | "BUY"/"SELL" — matches |
| `quantity` | `order.totalQuantity` | ✅ |
| `order_type` | `order.orderType` | "MARKET"→"MKT", "LIMIT"→"LMT", "STOP"→"STP" |
| `limit_price` | `order.lmtPrice` | ✅ |
| `stop_price` | `order.auxPrice` | ✅ |
| `tif` | `order.tif` | ✅ "DAY","GTC","IOC" |
| ❌ Missing | `order.transmit` | Add to `OrderRequest` — controls auto-transmission |
| ❌ Missing | `order.parentId` | Needed for bracket orders |

**Gap in `OrderRequest`:** No `broker_contract_id` / `conId` field. IBKR requires a `Contract` object with `symbol`, `secType`, `exchange`, `currency`. The `IBKRAdapter.submit_order()` will need to call `reqContractDetails` first to resolve the contract, or cache contract IDs in `Asset` table.

### 5.2 Order Status Tracking
Response: `EWrapper.orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, ...)`  
Status values: `PendingSubmit`, `PreSubmitted`, `Submitted`, `Filled`, `Cancelled`, `Inactive`

**Cross-reference with `OrderStatus` enum in `db/enums.py`** — verify these values are mapped.

Response: `EWrapper.openOrder(orderId, contract, order, orderState)`  
Response: `EWrapper.execDetails(reqId, contract, execution)` — fills with price/qty  
Response: `EWrapper.commissionAndFeesReport(report)` — commission per fill

**Gap:** `PaperOrder` has no `broker_order_id` (IBKR `permId`), `commission` field, or `exchange_filled` field. Live orders need these for reconciliation.

### 5.3 Supported Order Types
From IBKR SMART routing on NASDAQ/NYSE:
- `MKT` — Market order
- `LMT` — Limit order  
- `STP` — Stop order (maps to `auxPrice`)
- `STP LMT` — Stop-limit order
- `TRAIL` — Trailing stop (% or $)
- `TRAIL LIMIT` — Trailing stop-limit
- `MOC` — Market on close
- `LOC` — Limit on close
- `REL` — Relative/pegged order
- `MIDPX` — Mid-price order
- `SCALE` — Scale order
- `ALGO` types: IBKRATS, VWAP, TWAP, DarkIce, etc.

**Current `OrderRequest.order_type` supports:** `MARKET`, `LIMIT`, `STOP` — expand to include `STOP_LIMIT`, `TRAIL`, `MOC` for richer execution.

### 5.4 Bracket Orders
```python
# Parent
parent = Order()
parent.orderId = next_id
parent.action = "BUY"
parent.orderType = "LMT"
parent.totalQuantity = 100
parent.lmtPrice = entry_price
parent.transmit = False  # hold until children sent

# Profit taker
profit = Order()
profit.action = "SELL"
profit.orderType = "LMT"
profit.lmtPrice = target_price
profit.parentId = parent.orderId
profit.transmit = False

# Stop loss
stop = Order()
stop.action = "SELL"
stop.orderType = "STP"
stop.auxPrice = stop_price
stop.parentId = parent.orderId
stop.transmit = True  # transmit all at once

app.placeOrder(parent.orderId, contract, parent)
app.placeOrder(profit_id, contract, profit)
app.placeOrder(stop_id, contract, stop)
```

**This is critical for the existing workflow:** The `PaperExecutionRequest` already has `stop_price` and `target_price`. Bracket order support should be a first-class feature in `IBKRAdapter.submit_order()`.

### 5.5 Cancel Order
Function: `EClient.cancelOrder(orderId, OrderCancel())`  
Function: `EClient.reqGlobalCancel(OrderCancel())` — cancels ALL open orders

### 5.6 WhatIf Orders (Margin Pre-Check)
Set `order.whatIf = True` before calling `placeOrder` — returns margin impact without submitting.  
Response comes to `EWrapper.openOrder` with `orderState.initMarginChange`, `maintMarginChange`.

**Use as pre-flight in `execution_safety_gate.py`** (Phase 15.2).

---

## 6. Contract Resolution

IBKR requires a `Contract` object, not just a ticker symbol.

```python
contract = Contract()
contract.symbol = "AAPL"
contract.secType = "STK"       # STK, OPT, FUT, FOREX, IND, CFD, etc.
contract.exchange = "SMART"    # Smart routing
contract.primaryExch = "NASDAQ"
contract.currency = "USD"
```

To get `conId` (numeric contract identifier needed for PnL subscription):
```python
self.reqContractDetails(reqId, contract)
# Response: EWrapper.contractDetails(reqId, contractDetails)
# contractDetails.contract.conId
```

To search by symbol:
```python
self.reqMatchingSymbols(reqId, "AAPL")
# Response: EWrapper.symbolSamples(reqId, contractDescriptions)
```

**Gap in `Asset` model:** No `broker_contract_id` (IBKR `conId`) field. Recommend adding `ibkr_con_id: int` column to `Asset` table to cache resolved contract IDs and avoid redundant `reqContractDetails` calls.

---

## 7. Rate Limits & Pacing

| Limit Type | Value |
|---|---|
| Max API messages per second | 50 msg/s (error 100 → disconnect) |
| Max active market data lines | 100 (default) — determines request rate |
| Max requests per second | `market_data_lines / 2` (default = 50/s) |
| Historical data pacing | Max 60 requests per 10 minutes; no identical request within 15 seconds |
| reqHeadTimestamp | Counts as an ongoing historical data request |
| Tick-by-tick subscriptions | Max 5% of total market data lines (= 5 default) |
| reqAccountSummary update frequency | Every 3 minutes (fixed) |
| reqPnL updates | ~1/second |

**Design implication:** The `data_sync_scheduler.py` and `data_sync_worker.py` must enforce pacing. Add a request queue with rate limiting (e.g., `asyncio.Queue` + semaphore) in `IBKRClientService`.

---

## 8. Corporate Events (Wall Street Horizon)

Function: `EClient.reqWshMetaData(reqId)` → then `EClient.reqWshEventData(reqId, WshEventData)`  
Requires: Wall Street Horizon subscription in Account Management.

**Available event types:**
- `wshe_ed` — Earnings date
- `wshe_eps` — Earnings report
- `wshe_div` — Dividend
- `wshe_splits` — Stock splits
- `wshe_merg_acq` — M&A events
- `wshe_sec` — SEC filing due dates

**Cross-reference:** No corporate events model exists yet. This data could enrich `Signal` generation — avoid trading near earnings dates, adjust risk on split dates, etc. Map to `news_article.py` or create dedicated `corporate_event.py` model.

---

## 9. News Integration

Default subscribed news providers (no extra cost):
- `BRFG` — Briefing.com General Market Columns
- `BRFUPDN` — Briefing.com Analyst Actions  
- `DJNL` — Dow Jones Newsletters

**API pattern:**
```python
# Subscribe to contract-specific news
self.reqMktData(reqId, contract, "mdoff,292:BRFG+BRFUPDN+DJNL", False, False, [])
# Response: EWrapper.tickNews(tickerId, timeStamp, providerCode, articleId, headline, extraData)

# Fetch full article
self.reqNewsArticle(reqId, providerCode, articleId, [])
# Response: EWrapper.newsArticle(reqId, articleType, articleText)
```

**Cross-reference:** `news_article.py` model and `news_ingest_worker.py` already exist. Currently using Polygon for news. IBKR news feeds provide institutional-quality headlines from Briefing.com and Dow Jones at no additional API cost. Should augment existing `news_client.py`.

---

## 10. Error Handling Reference

Key error codes for Phase 15:
| Code | Meaning | Action |
|---|---|---|
| `502` | Cannot connect to TWS | Check TWS running, port, firewall |
| `326` | Client ID already in use | Use unique `clientId` per service |
| `100` | Max 50 msg/s exceeded | Add rate limiter |
| `101` | Max market data tickers exceeded | Cancel unused subscriptions |
| `110` | Order price out of range | Add pre-trade price sanity check |
| `201` | Order rejected | Parse `errorMsg` and log to `audit_log` |
| `202` | Order cancelled | Update order status |
| `1100` | TWS disconnected from IB servers | Reconnect logic in worker |
| `1101` | Reconnected — data lost | Re-subscribe all market data |
| `1102` | Reconnected — data maintained | No action needed |
| `2104/2106` | Data farm OK | Normal — connection established |
| `2110` | TWS↔server connectivity broken | Retry / circuit breaker |

---

## 11. Codebase Cross-Reference & Gap Analysis

### 11.1 `IBKRAdapter` (existing scaffold)
**File:** `app/clients/broker/ibkr_adapter.py`  
**Current state:** Placeholder — all methods raise `NotImplementedError`  
**What it needs for Phase 15:**
```
+ Import: from ibapi.client import EClient; from ibapi.wrapper import EWrapper
+ OR: from ibapi.sync_wrapper import TWSSyncWrapper (simpler for MVP)
+ submit_order() → call reqContractDetails() then placeOrder()
+ cancel_order() → call cancelOrder(orderId, OrderCancel())
+ get_account_info() → call reqAccountSummary() with AllTags
+ Add: get_positions() → reqPositions() [not in BrokerInterface yet]
+ Add: subscribe_pnl() → reqPnL() + reqPnLSingle()
```

**Recommendation:** Use `TWSSyncWrapper` for the initial implementation (v10.40+). It simplifies the threading model. Fall back to full EClient/EWrapper when streaming subscriptions are needed.

### 11.2 `BrokerInterface` (protocol)
**File:** `app/clients/broker/broker_interface.py`  
**Gaps to fill for Phase 15:**
```python
# Add to AccountInfo:
excess_liquidity: Decimal
maintenance_margin: Decimal
unrealized_pnl: Decimal
realized_pnl: Decimal
gross_position_value: Decimal

# Add to OrderRequest:
broker_contract_id: int | None = None   # IBKR conId
transmit: bool = True                    # hold-and-transmit for brackets
parent_id: int | None = None             # bracket order parent

# Add to OrderResult:
broker_perm_id: int | None = None        # IBKR permId (persistent)
commission: Decimal | None = None
exchange: str | None = None

# New methods on BrokerInterface:
async def get_positions(self) -> list[PositionInfo]: ...
async def get_executions(self, filter=None) -> list[ExecutionInfo]: ...
```

### 11.3 `Position` model
**File:** `app/db/models/position.py`  
**Gaps:**
```python
# Add:
broker_order_id: str | None        # IBKR orderId reference
broker_perm_id: int | None         # IBKR permId (survives restarts)
ibkr_con_id: int | None            # IBKR conId for PnL subscription
market_value: float | None         # missing from IBKR updatePortfolio
commission_paid: float | None      # cumulative commission for position
```

### 11.4 `PaperOrder` model
**File:** `app/db/models/paper_order.py`  
**Gaps for live orders (consider creating `live_order.py`):**
```python
# For live orders add:
broker_order_id: str                # IBKR orderId
broker_perm_id: int | None          # IBKR permId
commission: float | None            # from commissionReport callback
exchange_filled: str | None         # exchange where fill occurred
avg_fill_price: float | None        # from execDetails callback
ibkr_status: str | None             # raw IBKR order status string
```

### 11.5 `Asset` model
**File:** `app/db/models/asset.py`  
**Gap:**
```python
# Add:
ibkr_con_id: int | None             # cache IBKR conId to avoid repeated reqContractDetails
ibkr_primary_exchange: str | None   # e.g. "NASDAQ", "NYSE"
ibkr_currency: str = "USD"          # default USD
```

### 11.6 `Bar` model
**File:** `app/db/models/bar.py`  
**Currently:** `open, high, low, close, volume, vwap, source`  
**IBKR provides additionally:**  
`barCount` (number of trades in bar) — useful for volume quality assessment. The existing `vwap` column maps to IBKR's `bar.wap`.

### 11.7 `PnlSnapshot` model
**File:** `app/db/models/pnl_snapshot.py`  
**Well-structured for IBKR data.** The `ibkr_position_monitor.py` worker should:
1. Subscribe `reqPnL(reqId, account, "")` → updates `open_pnl`, `closed_pnl`
2. Subscribe `reqAccountUpdates(True, account)` → updates `equity`, `cash`, `gross_exposure`
3. Write to `pnl_snapshots` at configurable interval (e.g., every minute)

### 11.8 `execution_mode_service.py`
**File:** `app/services/execution_mode_service.py`  
Active mode is `auto_paper` — routes to `PaperExecutionService`. Phase 15 wires `auto_live` → `LiveExecutionService` → `IBKRAdapter`.

The execution mode gate needs to check:
```python
if mode == "auto_live":
    # Pre-flight: reqAccountSummary → check BuyingPower, ExcessLiquidity
    # WhatIf order → check margin impact
    # Only then: IBKRAdapter.submit_order()
```

---

## 12. Implementation Recommendations (Maximise API Usage)

### Priority 1 — Phase 15 Core (Required for Live Trading)
1. **Implement `IBKRAdapter`** using `TWSSyncWrapper` for orders + `EClient/EWrapper` for streaming
2. **Add `ibkr_con_id` to `Asset` model** — cache contract IDs on first resolution
3. **Add `broker_order_id`, `commission` to order model** — essential for reconciliation
4. **Implement `execution_safety_gate.py`** using `reqAccountSummary` + WhatIf pre-check
5. **Implement `ibkr_position_monitor.py` worker** using `reqPositions` + `reqPnL`

### Priority 2 — Data Enrichment (Maximise API Data)
6. **Replace/augment Polygon market data** with IBKR real-time bars (`reqRealTimeBars`)
7. **Add generic ticks** to market data requests: `104,165,225,232,233,236` — adds HV, IV, mark price, shortable, T&S to signal features
8. **Use `ADJUSTED_LAST`** in `reqHistoricalData` for corporate-action-adjusted backtests
9. **Add WAP/barCount** fields to `Bar` model from IBKR historical data

### Priority 3 — Advanced Capabilities
10. **L2 Market Depth** — feed into existing `liquidity.py` indicator for order book imbalance
11. **Market Scanner integration** — use `reqScannerSubscription` to discover opportunities, feed into `opportunity_ranker_service.py`
12. **Wall Street Horizon events** — avoid trading near earnings/splits, enrich signal context
13. **IBKR News** (BRFG, DJNL) — augment `news_ingest_worker.py` alongside Polygon news
14. **Tick-by-tick data** — for high-precision entry timing once paper learning loop validates strategy
15. **Options Greeks** — if options trading added, use `reqMktData` with `genericTickList="13"` for live model Greeks

### Priority 4 — Risk Maximisation
16. **WhatIf pre-trade margin check** — call `placeOrder` with `order.whatIf=True` before every live order
17. **reqGlobalCancel** as kill switch — wire to `/execution/kill-switch` endpoint
18. **Reconnection logic** — handle error codes 1100/1101 in `IBKRAdapter` to re-subscribe on disconnect
19. **Max pacing compliance** — add request queue with `asyncio.Semaphore(50)` at 1-second intervals

---

## 13. Phase 15 Architecture Alignment

The existing `phase-15-broker-integration-plan.md` references an HTTP REST client (`IBKRClientService`). **This conflicts with the existing `ibkr_adapter.py` scaffold which uses TWS socket pattern.**

**Resolution:** Keep `ibkr_adapter.py` as the broker client (TWS pattern, already scaffolded). The phase-15 plan's `IBKRClientService` should be renamed/merged into `ibkr_adapter.py` using the native Python `ibapi` package rather than REST calls. The Web/REST API (Client Portal) is less capable and adds OAuth complexity.

**Updated module map:**
| Phase 15 Module | File | Approach |
|---|---|---|
| IBKR Client | `app/clients/broker/ibkr_adapter.py` (implement) | `ibapi` TWS Python package |
| Position Monitor | `app/workers/ibkr_position_monitor.py` | `reqPositions()` + `reqPnL()` subscription |
| Execution Safety | `app/services/execution_safety_gate.py` | WhatIf + reqAccountSummary |
| Live Execution | `app/services/live_execution_service.py` (rewrite) | Calls `IBKRAdapter.submit_order()` |

**Install:** `pip install ibapi` or from TWS API download: `cd ~/TWS\ API/source/pythonclient && python setup.py install`

---

## 14. Quick-Reference Code Patterns

### Minimal order submission (TWS API Python)
```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading, time

class IBKRClient(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id = None

    def nextValidId(self, orderId: int):
        self.next_order_id = orderId

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, *args):
        # Update order in DB here
        pass

    def execDetails(self, reqId, contract, execution):
        # Record fill in DB here
        pass

    def commissionAndFeesReport(self, report):
        # Record commission in DB here
        pass

app = IBKRClient()
app.connect("127.0.0.1", 7497, clientId=1)  # paper port
threading.Thread(target=app.run, daemon=True).start()
time.sleep(1)  # wait for nextValidId

contract = Contract()
contract.symbol = "AAPL"
contract.secType = "STK"
contract.exchange = "SMART"
contract.currency = "USD"

order = Order()
order.action = "BUY"
order.orderType = "LMT"
order.totalQuantity = 100
order.lmtPrice = 200.00
order.tif = "DAY"

app.placeOrder(app.next_order_id, contract, order)
```

### Account info fetch (Sync Wrapper)
```python
from ibapi.sync_wrapper import TWSSyncWrapper
from ibapi.account_summary_tags import AccountSummaryTags

app = TWSSyncWrapper(timeout=30)
app.connect_and_start("127.0.0.1", 7497, client_id=0)
summary = app.get_account_summary(AccountSummaryTags.AllTags, "All")
# Returns: {account_id: {tag: {value, currency}}}
net_liq = float(summary["U1234567"]["NetLiquidation"]["value"])
```

---

*Knowledge bank built from IBKR Campus TWS API Documentation + codebase analysis of market-hunter-mvp.*  
*Cross-reference complete: all existing models, services, and interfaces reviewed against IBKR API capabilities.*
