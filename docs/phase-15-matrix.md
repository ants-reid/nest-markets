# Phase 15 Implementation Matrix — IBKR Broker Integration

| ID | Component | Type | Status | Impl | Doc | Tests | Notes |
|---|---|---|---|---|---|---|---|
| API-B01 | IBKRAdapter | Service | implemented | ✓ | ✓ | ✓ | Full REST API 2.30.0 client: connect, orders, positions, account, market data |
| API-B02 | BrokerGatewayFactory | Service | implemented | ✓ | ✓ | ✓ | Factory for creating broker adapters; supports IBKR |
| API-S13 | BrokerService | Service | implemented | ✓ | ✓ | ✓ | Orchestration layer: order submission, position reconciliation, account management |
| API-R07 | /broker routes | Route | implemented | ✓ | ✓ | ✓ | GET /account, GET /positions, POST /orders, DELETE /orders/{id}, GET /orders/{id}/status, POST /reconcile |

## Test Counts

- **IBKRAdapter tests** (tests/clients/test_ibkr_adapter.py): 27 tests covering session mgmt, orders, positions, market data, options chain
- **BrokerService tests** (tests/services/test_broker_service.py): 19 tests covering factory, service, order submission, position reconciliation
- **Broker routes tests** (tests/routes/test_broker_routes.py): 8 tests covering all 5 endpoints
- **Total Phase 15 tests**: 54 tests (all passing)

## API Contracts

### GET /broker/account
Returns `AccountInfo` with balances and margin details.

### GET /broker/positions
Returns list of `PositionInfo` with open positions.

### POST /broker/orders
Request: `OrderRequestSchema` (ticker, side, quantity, order_type, limit_price, stop_price, tif, outside_rth, client_order_id)
Response: `OrderResultSchema` (broker_order_id, status, filled_price, filled_quantity, error_message)

### DELETE /broker/orders/{broker_order_id}
Cancels an order. Returns 404 if order not found.

### GET /broker/orders/{broker_order_id}/status
Returns raw order status dict from `get_order_status()`.

### POST /broker/reconcile
Request: `dict[str, float]` — ticker → expected quantity
Response: `ReconciliationReportSchema` — matched count, mismatches, actual positions

## Deferred (P3)

Remaining Phase 15 items per build-plan.md:
- BP-15.00: IB Client Portal Gateway setup (manual)
- BP-15.01: Compliance forms (manual)
- BP-15.04: AccountInfo fields + get_positions() (deferred; interface ready)
- BP-15.10–BP-15.42: Advanced features (contract lookup, complex order types, flex reconciliation, etc.)
