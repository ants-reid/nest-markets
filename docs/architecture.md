# Market Hunter Architecture

## Purpose
Market Hunter is a professional-grade AI-assisted trading platform with two execution modes:

1. Auto Trade Mode  
   The system can automatically execute trades within strict user-defined capital caps and risk limits.

2. Confirm Before Trade Mode  
   The system analyses the market, generates trade ideas, and prepares trades, but must wait for user approval before placing any live order.

The system must support a staged rollout:
- simulation
- paper trading
- guarded live trading

## Core principles
- AI proposes, deterministic rules approve
- no AI component may place orders directly
- risk rules always apply regardless of execution mode
- execution mode changes routing, not signal quality
- all critical decisions must be logged and auditable
- provider-specific logic must stay inside provider adapters
- live trading must remain disabled in MVP

## Core layers

### 1. Data ingestion layer
Responsible for:
- market data
- quotes
- bars
- spreads
- market status
- news
- macro data

### 2. Feature layer
Responsible for:
- indicators
- volatility
- trend
- relative strength
- market quality
- correlation groups

### 3. AI signal layer
Responsible for:
- structured signal generation
- catalyst classification
- trade review summarisation

This layer proposes only.

### 4. Risk layer
Responsible for:
- capital caps
- position limits
- drawdown limits
- spread checks
- session checks
- cooldown rules
- kill switch rules

### 5. Execution mode router
Responsible for routing approved trades to:
- paper execution
- pending user approval
- live execution

### 6. Paper execution layer
Responsible for:
- fake orders
- fake fills
- paper positions
- paper P&L

### 7. Live execution layer
Responsible for:
- broker orders
- broker sync
- execution state tracking

### 8. Approval workflow
Responsible for:
- approval requests
- approve/reject/expire actions
- approval audit trail

### 9. Dashboard layer
Responsible for:
- signals
- trades
- approvals
- risk settings
- audit logs
- prompt versions
- evaluation results

## Provider direction
- OpenAI: primary AI provider
- IBKR: long-term live execution broker
- Polygon: primary market data provider
- Postgres: primary structured database

## Anti-drift rules
- no LLM calls outside the LLM provider layer
- no broker calls outside the broker adapter layer
- no business logic in route files
- no mixed signal + execution service
- no mixed paper + live execution class
- no prompt strings embedded in service logic
