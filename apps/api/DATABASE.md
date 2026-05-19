# Market Hunter Database Setup

## Database Models

All database models are defined in `app/db/models/`. Each model lives in its own file following SQLAlchemy 2 patterns.

### Model Organization

```
app/db/models/
├── __init__.py            # Exports all models
├── asset.py               # Assets (stocks, ETFs, forex, etc.)
├── bar.py                 # OHLCV candles
├── quote.py               # Bid/ask snapshots
├── news_article.py        # Market news
├── feature_snapshot.py    # Technical indicators and features
├── prompt_version.py      # Versioned AI prompts
├── model_version.py       # Versioned ML models
├── signal.py              # AI-generated trading signals
├── risk_decision.py       # Risk layer approval decisions
├── paper_order.py         # Paper trading orders
├── paper_fill.py          # Paper order fills
├── position.py            # Open trading positions
├── pnl_snapshot.py        # Daily P&L snapshots
├── eval_case.py           # Backtest evaluation cases
├── eval_run.py            # Backtest evaluation results
├── audit_log.py           # Audit trail
├── approval_request.py    # User trade approvals
├── risk_profile.py        # Risk configuration
├── execution_mode.py      # Execution mode definitions
└── execution_policy.py    # Trade routing policies
```

## Migrations with Alembic

All database schema changes are managed with Alembic. This ensures:
- Version control of schema changes
- Forward and backward compatibility
- Team coordination on schema updates

### Running Migrations

**Initialize database with all Phase 2 tables:**

```bash
cd apps/api
poetry run alembic upgrade head
```

**Verify migration status:**

```bash
poetry run alembic current
```

**Downgrade if needed:**

```bash
poetry run alembic downgrade -1
```

### Creating New Migrations

After modifying models, generate a new migration:

```bash
poetry run alembic revision --autogenerate -m "Description of changes"
poetry run alembic upgrade head
```

## Schema Overview

### Key Design Patterns

1. **UUID Primary Keys**: All tables use UUID v4 for distributed system compatibility
2. **Timestamps**: All core tables include `created_at` and `updated_at` timestamps
3. **Indexes**: Strategic indexes on foreign keys, timestamps, and frequently queried columns
4. **Audit Trail**: `AuditLog` table tracks all critical system decisions
5. **Status Columns**: Explicit status fields (e.g., order status: pending, filled, canceled)

### Data Flow

```
Assets → Quotes/Bars → Features → Signals → Risk Decisions → Orders/Positions
                              ↓                    ↓
                        News Articles         Approval Requests
                        
All critical decisions logged to Audit Logs
```

### Configuration Tables

- **RiskProfile**: Risk limits and thresholds (MVP defaults defined)
- **ExecutionMode**: Execution modes (paper, pending_approval, live)
- **ExecutionPolicy**: Routing logic for approved trades
- **PromptVersion**: Versioned AI prompts (immutable when active)
- **ModelVersion**: Versioned ML models (immutable when active)

## Conservative Defaults

All models follow conservative defaults:
- Status fields default to "inactive" or "pending"
- Boolean-like fields use String(20) for explicit state representation
- Nullable fields are only used where appropriate
- No silent defaults or hidden state

## No Business Logic

Database models contain ONLY:
- Column definitions with types
- Relationships and constraints
- Simple `__repr__` methods for debugging
- No validation
- No computed properties
- No methods with side effects

All business logic lives in service layers (Phase 5+).

## Next Steps

After Phase 2 database foundation is solid:
1. Seed data (assets, execution modes, risk profiles)
2. Phase 3: Indicators and feature engine
3. Phase 4: LLM provider integration
4. Phase 5: Signal and risk services
