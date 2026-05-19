# Phase 2 Complete: Database Models and Migrations

## Created Files

### 20 Database Models (one file per model)

1. **Asset** (`app/db/models/asset.py`) - Tradable instruments with unique symbol/type constraint
2. **Bar** (`app/db/models/bar.py`) - OHLCV candles with timeframe aggregation
3. **Quote** (`app/db/models/quote.py`) - Bid/ask snapshots with spread calculation
4. **NewsArticle** (`app/db/models/news_article.py`) - Market news with sentiment
5. **FeatureSnapshot** (`app/db/models/feature_snapshot.py`) - Technical indicators and trend analysis
6. **PromptVersion** (`app/db/models/prompt_version.py`) - Versioned AI prompts (immutable when active)
7. **ModelVersion** (`app/db/models/model_version.py`) - Versioned ML models
8. **Signal** (`app/db/models/signal.py`) - AI-generated signals with confidence and catalyst
9. **RiskDecision** (`app/db/models/risk_decision.py`) - Risk layer approval with blocking rules
10. **PaperOrder** (`app/db/models/paper_order.py`) - Simulated orders for paper trading
11. **PaperFill** (`app/db/models/paper_fill.py`) - Fills for paper orders
12. **Position** (`app/db/models/position.py`) - Open trading positions with unrealized P&L
13. **PnlSnapshot** (`app/db/models/pnl_snapshot.py`) - Daily performance metrics
14. **EvalCase** (`app/db/models/eval_case.py`) - Backtest test scenarios
15. **EvalRun** (`app/db/models/eval_run.py`) - Backtest results with performance metrics
16. **AuditLog** (`app/db/models/audit_log.py`) - Comprehensive decision audit trail
17. **ApprovalRequest** (`app/db/models/approval_request.py`) - User trade approvals
18. **RiskProfile** (`app/db/models/risk_profile.py`) - Risk configuration (MVP defaults)
19. **ExecutionMode** (`app/db/models/execution_mode.py`) - Execution mode definitions
20. **ExecutionPolicy** (`app/db/models/execution_policy.py`) - Trade routing policies

### Model Exports

- **`app/db/models/__init__.py`** - Exports all 20 models for easy importing

### Alembic Migration Infrastructure

- **`alembic/env.py`** - Alembic environment configuration
- **`alembic/script.py.mako`** - Migration template
- **`alembic.ini`** - Alembic settings
- **`alembic/versions/001_initial_tables.py`** - Initial migration creating all 20 tables with 40+ indexes
- **`alembic/__init__.py`** - Package marker
- **`alembic/versions/__init__.py`** - Package marker

### Documentation

- **`DATABASE.md`** - Complete database setup guide with migration instructions
- **`MODELS_SUMMARY.md`** - This file

## Database Schema Summary

### 20 Tables Created

| Table | Purpose | Key Fields | Relationships |
|-------|---------|-----------|---------------|
| assets | Tradable instruments | symbol, asset_type, name | Referenced by: bars, quotes, news, features, signals, orders, positions |
| bars | OHLCV candles | asset_id, timestamp, timeframe, ohlcv | Asset FK |
| quotes | Bid/ask snapshots | asset_id, timestamp, bid/ask | Asset FK |
| news_articles | Market news | asset_id, headline, sentiment | Asset FK |
| feature_snapshots | Technical indicators | asset_id, timestamp, rsi, sma, atr, bb | Asset FK |
| prompt_versions | AI prompts | name, role, version, is_active | Referenced by: signals, eval_runs |
| model_versions | ML models | name, model_type, version, is_active | Referenced by: eval_runs |
| signals | AI signals | asset_id, prompt_id, direction, confidence | Asset FK, PromptVersion FK |
| risk_decisions | Risk approval | signal_id, risk_profile_id, approved | Signal FK, RiskProfile FK |
| paper_orders | Simulated orders | asset_id, risk_decision_id, direction, qty | Asset FK, RiskDecision FK |
| paper_fills | Order fills | paper_order_id, quantity, price | PaperOrder FK |
| positions | Open positions | asset_id, execution_mode, direction, qty | Asset FK |
| pnl_snapshots | Daily P&L | timestamp, total_pnl, return_pct | Independent |
| eval_cases | Backtest scenarios | name, date_range, assets, parameters | Referenced by: eval_runs |
| eval_runs | Backtest results | eval_case_id, prompt_id, model_id, returns | EvalCase FK, PromptVersion FK, ModelVersion FK |
| audit_logs | Decision audit trail | event_type, entity_id, action, risk_level | Independent |
| approval_requests | User approvals | risk_decision_id, status, approved_by | RiskDecision FK |
| risk_profiles | Risk configuration | name, max_positions, limits, thresholds | Referenced by: risk_decisions, execution_policies |
| execution_modes | Execution modes | name, requires_approval, allows_live | Referenced by: execution_policies, positions |
| execution_policies | Trade routing | execution_mode_id, risk_profile_id, logic | ExecutionMode FK, RiskProfile FK |

## Key Design Decisions

### 1. UUID Primary Keys
- All tables use PostgreSQL UUID type for distributed system compatibility
- Generated with `uuid4()` at application level or database default

### 2. Timestamps
- All core tables include `created_at` (immutable)
- Most core tables include `updated_at` (auto-updated)
- Timezone-aware: `DateTime(timezone=True)`
- Server-side defaults for consistency

### 3. Strategic Indexing
- Foreign keys indexed for join performance
- Timestamps indexed for time-range queries
- Status columns indexed for filtering
- Asset IDs indexed for asset-specific queries
- ~40+ total indexes across all tables

### 4. Audit Trail
- `AuditLog` table records all critical decisions
- Tracks: event_type, entity_type, entity_id, action, actor, risk_level
- Enables compliance and debugging

### 5. Status Fields
- Use explicit String(20) instead of boolean
- Allows for multi-state tracking
- Examples: "pending", "filled", "canceled", "approved", "rejected"

### 6. Risk Configuration
- `RiskProfile` stores MVP risk defaults
- Can be extended for custom risk profiles
- Referenced by `RiskDecision` and `ExecutionPolicy`

### 7. Signal to Order Flow
```
Signal → RiskDecision → ApprovalRequest → PaperOrder → PaperFill → Position
```

## Running Migrations

### Initial Setup

```bash
cd apps/api

# Install with Alembic
poetry install

# Create database
createdb market_hunter

# Run initial migration
poetry run alembic upgrade head
```

### Verify Migration

```bash
poetry run alembic current
# Output: 001_initial_tables
```

### Schema Statistics

- **20 tables**
- **40+ indexes**
- **UUID primary keys everywhere**
- **Comprehensive foreign key constraints**
- **Zero business logic** (models only define schema)

## Constraints and Uniqueness

### Unique Constraints

| Table | Constraint | Purpose |
|-------|-----------|---------|
| assets | symbol | One symbol per asset type |
| assets | symbol + asset_type | Prevent duplicates across types |
| bars | asset_id + timestamp + timeframe | One bar per asset per time per frame |
| prompt_versions | Implicit via name/role/version | Versioning by role |
| model_versions | Implicit via name/version | Versioning by model |
| execution_modes | name | One per mode type |
| risk_profiles | name | One per profile |
| execution_policies | name | One per policy |
| eval_cases | name | One per test case |
| pnl_snapshots | timestamp | One snapshot per timestamp |

## Foreign Keys (All CASCADE)

- Asset → Bar, Quote, NewsArticle, FeatureSnapshot, Signal, PaperOrder, Position
- PromptVersion → Signal, EvalRun
- ModelVersion → EvalRun
- Signal → RiskDecision
- RiskProfile → RiskDecision, ExecutionPolicy
- ExecutionMode → ExecutionPolicy
- RiskDecision → PaperOrder, ApprovalRequest
- PaperOrder → PaperFill
- EvalCase → EvalRun

## Conservative Defaults

Every model follows strict defaults:
- No implicit state changes
- Explicit status fields (no boolean confusion)
- Timestamps auto-managed by database
- Nullable only where semantically correct
- No computed columns (all at service layer)

## Next Phase (Phase 3)

After database foundation is solid:
1. Seed data: Assets, execution modes, risk profiles, prompts
2. Indicators: Deterministic feature calculations
3. Feature engine: Time-series computation

Only proceed when:
- All migrations run cleanly
- Schema reflects architecture correctly
- No business logic creep into models
