# Phase 15 — Broker Integration Implementation Plan

**Date:** 2026-04-24  
**Status:** Ready to Begin  
**Predecessor:** Phase 14 (RC-3 Post-Hardening Validation) ✅

---

## Executive Summary

Phase 15 introduces live trading execution via Interactive Brokers (IBKR). The system will:

1. **Maintain paper trading** as the default execution mode (no breaking changes)
2. **Add IBKR API client** layer (`IBKRClientService`)
3. **Implement live execution** in `LiveExecutionService` (replacing current scaffold)
4. **Add safety gates** (pre-execution confirmations, position limits, kill switch)
5. **Wire live execution route** (`POST /execution/live`) to IBKR orders
6. **Monitor position state** via IBKR account feed

---

## Architecture Overview

### Current State (RC-3)
```
POST /execution → WorkflowService → ApprovalService 
  → PaperExecutionService (paper orders)
  → LiveExecutionService (DISABLED: returns sentinel)
```

### Target State (Phase 15)
```
POST /execution → WorkflowService → ApprovalService 
  → SelectExecutionMode (paper vs live)
    → PaperExecutionService (paper orders)
    → LiveExecutionService (ENABLED: IBKR orders)
```

### New Components

| Module | File | Purpose |
|--------|------|---------|
| IBKR Client | `app/services/ibkr_client_service.py` | REST/WebSocket client to IBKR API |
| Live Execution | `app/services/live_execution_service.py` (rewrite) | Order submission, fills, cancellation |
| Position Monitor | `app/workers/ibkr_position_monitor.py` (Phase 7) | Polls account state; updates Position ORM |
| Execution Safety | `app/services/execution_safety_gate.py` | Pre-flight checks (limits, margin, halts) |

---

## Implementation Roadmap

### Phase 15.1 — IBKR Client Service (Week 1)

**Deliverable:** `IBKRClientService` with order/position/account APIs

#### BP-15.1.1 — Create IBKR client scaffold
- **File:** `apps/api/app/services/ibkr_client_service.py`
- **Purpose:** Thin HTTP client wrapping IBKR Account REST API
- **Key Methods:**
  - `__init__(account_id: str, api_key: str, base_url: str = "https://api.ibkr.com")`
  - `get_accounts() → List[IBKRAccount]`
  - `get_positions(account_id: str) → List[IBKRPosition]`
  - `get_account_info(account_id: str) → IBKRAccountInfo`
  - `create_order(account_id: str, order: IBKROrderRequest) → IBKROrderResponse`
  - `cancel_order(account_id: str, order_id: str) → bool`
  - `get_order_status(account_id: str, order_id: str) → IBKROrderStatus`

- **Data Models:**
  ```python
  class IBKRAccount(BaseModel):
      account_id: str
      account_type: str  # INDIVIDUAL, ORGANIZATION, etc.
      net_liquidation: float
      buying_power: float
      excess_liquidity: float
  
  class IBKRPosition(BaseModel):
      contract_id: str
      symbol: str
      qty: float
      avg_cost: float
      market_price: float
      market_value: float
      unrealized_pnl: float
  
  class IBKROrderRequest(BaseModel):
      contract_id: str
      action: str  # BUY or SELL
      order_type: str  # MKT, LMT, STP, etc.
      total_quantity: int
      lmt_price: Optional[float] = None
      aux_price: Optional[float] = None
      tif: str = "DAY"  # GTC, DAY, IOC, etc.
      transmit: bool = True
  
  class IBKROrderResponse(BaseModel):
      order_id: str
      status: str
      filled_quantity: int
      avg_fill_price: float
      commission: float
  ```

- **Configuration:** Read from env vars
  ```bash
  IBKR_ACCOUNT_ID=<account>
  IBKR_API_KEY=<key>
  IBKR_BASE_URL=https://api.ibkr.com
  IBKR_SANDBOX=false  # true for paper trading API
  ```

- **Tests:** 8 unit tests
  - Mock HTTP responses
  - Verify order request format
  - Confirm response parsing
  - Error handling (auth, network, API errors)

- **Status:** To implement

---

#### BP-15.1.2 — Add IBKR client tests to suite
- **File:** `apps/api/tests/services/test_ibkr_client_service.py`
- **Coverage:** 8 tests
  - `test_get_accounts_returns_account_list`
  - `test_get_positions_parses_contract_data`
  - `test_create_order_sends_correct_payload`
  - `test_order_status_polls_correctly`
  - `test_cancel_order_validates_account_id`
  - `test_handles_401_auth_error`
  - `test_handles_429_rate_limit`
  - `test_handles_network_timeout`

- **Status:** To implement

---

### Phase 15.2 — Rewrite LiveExecutionService (Week 2)

**Deliverable:** Production-ready live execution service (replaces scaffold)

#### BP-15.2.1 — Rewrite live_execution_service.py
- **File:** `apps/api/app/services/live_execution_service.py`
- **Replace:** Current scaffold (always returns `accepted=False`)
- **New Contract:**
  ```python
  class LiveExecutionService:
      def __init__(
          self, 
          session: Session,
          ibkr_client: IBKRClientService,
          safety_gate: ExecutionSafetyGate
      ):
          self._session = session
          self._ibkr_client = ibkr_client
          self._safety_gate = safety_gate
      
      def execute_live_order(
          self,
          signal: Signal,
          risk_profile: RiskProfile,
          execution_request: ExecutionRequest
      ) -> ExecutionResponse:
          """
          Validate signal/risk, apply safety gates, submit IBKR order,
          persist execution record.
          """
          # 1. Validate request
          if not execution_request.execution_mode == "auto_live":
              raise ValueError("Expected auto_live mode")
          
          # 2. Apply safety gates (position limits, margin, halts)
          gate_result = self._safety_gate.pre_flight_check(
              signal=signal,
              risk_profile=risk_profile,
              execution_request=execution_request
          )
          if not gate_result.approved:
              return ExecutionResponse(
                  accepted=False,
                  status="blocked",
                  reason=gate_result.rejection_reason,
                  order_id=None
              )
          
          # 3. Create IBKR order request
          ibkr_order = self._build_ibkr_order_request(signal, execution_request)
          
          # 4. Submit to IBKR
          try:
              ibkr_response = self._ibkr_client.create_order(
                  account_id=self._get_account_id(),
                  order=ibkr_order
              )
          except IBKRAPIError as e:
              return ExecutionResponse(
                  accepted=False,
                  status="error",
                  reason=f"IBKR API error: {e.message}",
                  order_id=None
              )
          
          # 5. Persist execution record (bridges IBKR order to Signal)
          execution = Execution(
              signal_id=signal.id,
              order_id=ibkr_response.order_id,
              execution_mode="auto_live",
              status="pending",
              notional=execution_request.notional,
              ibkr_order_id=ibkr_response.order_id,
              ibkr_status="PENDING"
          )
          self._session.add(execution)
          self._session.flush()
          
          return ExecutionResponse(
              accepted=True,
              status="pending",
              reason="Order submitted to IBKR",
              order_id=execution.id
          )
      
      def _build_ibkr_order_request(
          self,
          signal: Signal,
          execution_request: ExecutionRequest
      ) -> IBKROrderRequest:
          """Convert Signal + ExecutionRequest to IBKR order format."""
          # Map Signal direction to BUY/SELL
          action = "BUY" if signal.direction == TradeDirection.LONG else "SELL"
          
          # Use execution notional to size quantity
          qty = self._calculate_order_quantity(
              notional=execution_request.notional,
              current_price=signal.entry_price_suggestion or 1.0
          )
          
          return IBKROrderRequest(
              contract_id=self._get_contract_id(signal.asset_id),
              action=action,
              order_type="MKT",  # Market order for now (Phase 16: limit orders)
              total_quantity=int(qty),
              tif="DAY"
          )
      
      def _get_account_id(self) -> str:
          """Retrieve active IBKR account ID from config."""
          return os.getenv("IBKR_ACCOUNT_ID")
      
      def _get_contract_id(self, asset_id: UUID) -> str:
          """Map Asset UUID to IBKR contract ID."""
          # For now: hardcoded mapping (Phase 16: asset catalog with IBKR contract IDs)
          asset = self._session.query(Asset).filter(Asset.id == asset_id).one()
          if asset.symbol == "EURUSD":
              return "12087792"  # EURUSD = IB's contract ID
          raise ValueError(f"No IBKR contract mapping for {asset.symbol}")
      
      def _calculate_order_quantity(
          self,
          notional: float,
          current_price: float
      ) -> float:
          """Size order quantity from notional amount."""
          return notional / current_price
  ```

- **Key Differences from Scaffold:**
  - ✅ Actually submits orders to IBKR
  - ✅ Applies pre-flight safety gates
  - ✅ Persists execution record to Position/Execution ORM
  - ✅ Returns order ID (not sentinel)
  - ✅ Error handling for IBKR API failures

- **Status:** To implement

---

#### BP-15.2.2 — Create execution_safety_gate.py
- **File:** `apps/api/app/services/execution_safety_gate.py`
- **Purpose:** Pre-execution validation layer
- **Key Methods:**
  ```python
  class ExecutionSafetyGate:
      def __init__(self, session: Session):
          self._session = session
      
      def pre_flight_check(
          self,
          signal: Signal,
          risk_profile: RiskProfile,
          execution_request: ExecutionRequest
      ) -> SafetyGateResult:
          """
          Validate execution against configured limits:
          - Position capacity (not at max)
          - Margin availability (notional < buying_power)
          - Equity concentration (single-asset limit)
          - Daily trading limit (N orders/day)
          - Halt flags (emergency kill switch)
          """
          result = SafetyGateResult(approved=True)
          
          # 1. Position capacity check
          open_count = self._count_open_positions()
          if open_count >= self._get_max_positions():
              result.approved = False
              result.rejection_reason = f"Position limit reached ({open_count}/{self._get_max_positions()})"
              return result
          
          # 2. Margin check
          account_info = self._get_account_info()
          if execution_request.notional > account_info.excess_liquidity * 0.8:
              result.approved = False
              result.rejection_reason = "Insufficient margin (>80% of excess liquidity)"
              return result
          
          # 3. Concentration check
          existing_exposure = self._get_asset_exposure(signal.asset_id)
          total_exposure = existing_exposure + execution_request.notional
          if total_exposure > self._get_max_concentration():
              result.approved = False
              result.rejection_reason = f"Asset concentration limit exceeded"
              return result
          
          # 4. Daily trading limit
          today_count = self._count_trades_today()
          if today_count >= self._get_daily_trade_limit():
              result.approved = False
              result.rejection_reason = "Daily trade limit reached"
              return result
          
          # 5. Halt flag check
          if self._is_execution_halted():
              result.approved = False
              result.rejection_reason = "Execution halt is active"
              return result
          
          return result
  
  class SafetyGateResult(BaseModel):
      approved: bool
      rejection_reason: Optional[str] = None
  ```

- **Configuration (env):**
  ```bash
  EXECUTION_MAX_POSITIONS=6
  EXECUTION_MAX_CONCENTRATION_PCT=40
  EXECUTION_DAILY_TRADE_LIMIT=20
  EXECUTION_MARGIN_SAFETY_BUFFER=0.8
  ```

- **Tests:** 6 unit tests
  - Approve when all limits OK
  - Reject at max position capacity
  - Reject at insufficient margin
  - Reject at asset concentration limit
  - Reject when daily trade limit hit
  - Reject when halt flag set

- **Status:** To implement

---

### Phase 15.3 — Wire Live Execution Route (Week 2)

**Deliverable:** Production route connecting `POST /execution/live` to IBKR orders

#### BP-15.3.1 — Update execution.py route
- **File:** `apps/api/app/api/routes/execution.py`
- **Changes:**
  - Replace scaffold response with live execution call
  - Inject `IBKRClientService` and `ExecutionSafetyGate`
  - Validate execution_mode == "auto_live" on live route
  - Return actual IBKR order ID

- **Before (Scaffold):**
  ```python
  @router.post("/execution/live")
  def post_execution_live(
      req: ExecutionRequest,
      session: Session = Depends(get_db)
  ):
      return ExecutionResponse(
          accepted=False,
          status="disabled",
          reason="live_execution_disabled_in_mvp"
      )
  ```

- **After (Production):**
  ```python
  @router.post("/execution/live")
  def post_execution_live(
      req: ExecutionRequest,
      session: Session = Depends(get_db),
      ibkr_client: IBKRClientService = Depends(get_ibkr_client),
      safety_gate: ExecutionSafetyGate = Depends(get_safety_gate)
  ):
      # Fetch signal and risk
      signal = session.query(Signal).filter(Signal.id == req.signal_id).one()
      risk_profile = session.query(RiskProfile).filter(
          RiskProfile.signal_id == signal.id
      ).one()
      
      # Execute
      live_svc = LiveExecutionService(session, ibkr_client, safety_gate)
      result = live_svc.execute_live_order(signal, risk_profile, req)
      
      return result
  ```

- **Tests:** 4 new route tests
  - Live order accepted and returns IBKR order ID
  - Safety gate rejection blocks order
  - IBKR API error returns error response
  - Execution persists to database

- **Status:** To implement

---

### Phase 15.4 — Integration Tests & Staging (Week 3)

**Deliverable:** End-to-end test suite; staging validation

#### BP-15.4.1 — Create e2e live execution test
- **File:** `apps/api/tests/test_e2e_live_execution.py`
- **Test Flow:**
  1. Create signal (mock EURUSD)
  2. Evaluate risk
  3. Create execution request (auto_live)
  4. POST /execution/live
  5. Assert order ID returned
  6. Assert Position record created
  7. Assert Execution record persisted
  8. (Future) Simulate IBKR fill; assert Position.realized_pnl updated

- **Mocking:** Mock IBKR API responses; do NOT call production IBKR

- **Tests:** 5 comprehensive e2e tests
  - `test_live_execution_creates_order_and_position`
  - `test_live_execution_respects_safety_gates`
  - `test_live_execution_persists_to_database`
  - `test_live_execution_handles_ibkr_failure_gracefully`
  - `test_position_monitor_updates_filled_quantities` (foreshadow Phase 7)

- **Status:** To implement

---

#### BP-15.4.2 — Staging validation checklist
- **Prerequisites:**
  - Staging PostgreSQL with applied migrations (alembic upgrade head)
  - Staging IBKR sandbox account (paper trading mode)
  - Env vars configured: `IBKR_ACCOUNT_ID`, `IBKR_API_KEY`, `IBKR_SANDBOX=true`

- **Manual Tests:**
  1. ✅ Dashboard loads (verify no 404s)
  2. ✅ Generate signal via `/signals/generate`
  3. ✅ Evaluate risk
  4. ✅ Create execution request (paper mode)
  5. ✅ Verify paper order works (baseline)
  6. ✅ Create execution request (live mode, sandbox)
  7. ✅ Verify IBKR sandbox order received
  8. ✅ Check Position/Execution records in staging DB
  9. ✅ Safety gate rejects order at position limit
  10. ✅ Safety gate rejects order at insufficient margin

- **Rollback Plan:** If IBKR integration fails, disable via env var:
  ```bash
  LIVE_EXECUTION_ENABLED=false
  ```
  Route returns disabled sentinel (graceful fallback to RC-3 state).

- **Status:** To implement

---

## Risk Assessment

### What Could Go Wrong?

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| IBKR API key leak | Low | Critical | Keys in env vars only; rotate quarterly |
| Over-trading (position limit gap) | Medium | High | ExecutionSafetyGate + manual review before go-live |
| Margin call during overnight gap | Medium | High | Daily excess_liquidity check; dim orders at 70% threshold |
| Network latency → stale quotes | Medium | Medium | Use limit orders (Phase 16); require manual final approval |
| IBKR API rate limiting | Low | Medium | Exponential backoff; queue orders if needed |
| Production IBKR account → accidental live trade | Critical | Critical | **MANDATORY:** IBKR_SANDBOX=true until Phase 16 final approval |

### Mitigations

1. **Gate 4 (Live Execution Guard) extends to:**
   - ✅ Scaffold → Production transition only after stage validation
   - ✅ Env var `LIVE_EXECUTION_ENABLED=false` (default) until explicitly enabled
   - ✅ All orders require position_capacity check + margin check
   - ✅ Kill switch via halt flag in database

2. **Pre-Production Checklist:**
   - [ ] All 5 Phase 15.4.1 e2e tests passing
   - [ ] Staging paper/live flow validated manually
   - [ ] IBKR sandbox account tested for 24 hours
   - [ ] Daily position limit audit (auto-cancel stale orders)
   - [ ] Legal review of order transmit terms (IBKR TOS)
   - [ ] Stakeholder sign-off on production IBKR account

---

## Success Criteria

### Phase 15 Complete When:

- ✅ `IBKRClientService` implemented; 8/8 unit tests passing
- ✅ `LiveExecutionService` rewritten; 4/4 route tests passing
- ✅ `ExecutionSafetyGate` implemented; 6/6 unit tests passing
- ✅ E2E live execution tests (5/5) passing
- ✅ Staging validation checklist (10/10) completed
- ✅ Zero regressions in prior phases (all 355+ backend tests still passing)
- ✅ All 6 release gates still passing

### Test Suite Target:
- Current: 355/355 backend tests
- After Phase 15: **375+/375+ backend tests** (±20 new tests)

---

## Dependencies & Blockers

### External Dependencies:
- [ ] IBKR API account access (sandbox + production)
- [ ] IBKR API documentation (order spec, contract catalog)
- [ ] Production AWS/production-like PostgreSQL for final testing

### Internal Dependencies:
- ✅ Phase 14 (RC-3 validation) — COMPLETE
- ✅ Phase 6 (Execution & Approval) — COMPLETE
- ✅ Phase 3-5 (Signal/Risk/Features) — COMPLETE
- → Phase 15 can proceed immediately

### Blockers (None):
- No blocking architectural issues
- No prior features need refactoring
- Live execution scaffold in place; safe to replace

---

## Timeline Estimate

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| 15.1 — IBKR Client | 3-4 days | Yes (blocks all live execution) |
| 15.2 — Rewrite LiveExecution | 3-4 days | Yes (integrates IBKR client) |
| 15.3 — Wire Route | 1-2 days | Yes (final API integration) |
| 15.4 — Tests & Staging | 3-4 days | Yes (go-live validation) |
| **Total** | **10-14 days** | **~2 weeks** |

**Target Completion:** ~May 8, 2026 (if starting 2026-04-24)

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Provision IBKR sandbox account** (auto-approval for paper trading)
3. **Stage: Confirm Phase 14 RC-3 is deployed** to production or staging
4. **Begin BP-15.1.1** (IBKR client scaffold)
5. **Weekly sync** to track progress against risk mitigation checkpoints

---

## Appendix A: IBKR Integration Reference

### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/accounts` | List accounts |
| GET | `/accounts/{id}/positions` | Get open positions |
| GET | `/accounts/{id}` | Account summary (margin, NLV) |
| POST | `/accounts/{id}/orders` | Create order |
| DELETE | `/accounts/{id}/orders/{order_id}` | Cancel order |
| GET | `/accounts/{id}/orders/{order_id}` | Order status |

### Contract ID Mapping (Phase 16)

Currently hardcoded; should become configurable asset catalog:

```
EURUSD → 12087792 (IB conid)
GBPUSD → 12008129
USDJPY → 12106270
(expand per asset catalog)
```

### Order Status States

```
PENDING → FILLED | CANCELED | REJECTED
FILLED → CLOSED (upon position close)
CANCELED → (end state)
REJECTED → (end state; review reason)
```

---

## Appendix B: Glossary

- **IBKR** = Interactive Brokers
- **Sandbox** = IBKR's paper trading API (no real money)
- **Conid** = IBKR contract ID (maps symbol to tradeable contract)
- **NLV** = Net Liquidation Value (total account equity)
- **Excess Liquidity** = Available margin for new orders
- **TIF** = Time In Force (DAY, GTC, IOC, etc.)

---
