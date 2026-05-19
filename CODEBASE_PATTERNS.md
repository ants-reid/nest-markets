# Market Hunter MVP — Codebase Architecture Patterns

Complete guide to match existing codebase style precisely for database models, Alembic migrations, Pydantic schemas, services, routes, frontend API clients, types, and components.

---

## 1. Database Models (SQLAlchemy ORM)

**Location:** `apps/api/app/db/models/`

### Base Classes and Mixins

```python
# apps/api/app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""
```

```python
# apps/api/app/db/models/mixins.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

class UUIDPrimaryKeyMixin:
    """Mixin that provides a UUID primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

class TimestampMixin:
    """Mixin that provides created/updated timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

class CreatedAtMixin:
    """Mixin for tables that only need created_at."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

JSONBType = JSONB  # Type alias for JSONB columns
```

### Model Example: PaperValidationPlan

```python
# apps/api/app/db/models/paper_validation_plan.py
"""Paper validation plan model for MH-16 gate workflow."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class PaperValidationPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Validation gate plan linking a baseline candidate to paper proof requirements."""

    __tablename__ = "paper_validation_plans"

    baseline_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    backtest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    strategy_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )

    required_trades: Mapped[int] = mapped_column(nullable=False, default=100)
    minimum_days: Mapped[int] = mapped_column(nullable=False, default=30)

    target_profit_factor: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    max_drawdown_pct: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    max_daily_loss_pct: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    starting_paper_capital: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=200000
    )

    backtest_metrics: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    paper_metrics: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    progress: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    pass_fail_reasons: Mapped[list | dict | None] = mapped_column(JSONBType, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### Model Example: BaselineCandidate

```python
# apps/api/app/db/models/baseline_candidate.py
"""BaselineCandidate — research-stage candidate from strategy lab results."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin


class BaselineCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Research-stage baseline candidate. Not an activation or live approval."""

    __tablename__ = "baseline_candidates"

    backtest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    strategy_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    ai_backtest_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    asset: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    strategy_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    parameters: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="watchlist_candidate",
        index=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Key Patterns
- Use `from __future__ import annotations` at top for forward references
- Inherit from `UUIDPrimaryKeyMixin`, `TimestampMixin`, and `Base`
- Use `Mapped[type]` type hints for all columns
- Use `mapped_column()` for column definition with SQLAlchemy types
- Index foreign key relationships and status fields
- Use `JSONBType` alias for JSONB columns
- Add docstring to class describing its purpose

---

## 2. Alembic Migration Patterns

**Location:** `apps/api/alembic/versions/`

### Migration Structure

```python
# apps/api/alembic/versions/k6l7m8n9o0p1_add_mh16_paper_validation_plans.py
"""add_mh16_paper_validation_plans

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-04-28 10:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "k6l7m8n9o0p1"
down_revision = "j5k6l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_validation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("baseline_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("required_trades", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("minimum_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("target_profit_factor", sa.Numeric(12, 6), nullable=True),
        sa.Column("max_drawdown_pct", sa.Numeric(12, 6), nullable=True),
        sa.Column("max_daily_loss_pct", sa.Numeric(12, 6), nullable=True),
        sa.Column("starting_paper_capital", sa.Numeric(18, 4), nullable=False, server_default="200000"),
        sa.Column("backtest_metrics", postgresql.JSONB, nullable=True),
        sa.Column("paper_metrics", postgresql.JSONB, nullable=True),
        sa.Column("progress", postgresql.JSONB, nullable=True),
        sa.Column("pass_fail_reasons", postgresql.JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_paper_validation_plans_baseline_candidate_id", "paper_validation_plans", ["baseline_candidate_id"])
    op.create_index("ix_paper_validation_plans_backtest_run_id", "paper_validation_plans", ["backtest_run_id"])
    op.create_index("ix_paper_validation_plans_strategy_config_id", "paper_validation_plans", ["strategy_config_id"])
    op.create_index("ix_paper_validation_plans_status", "paper_validation_plans", ["status"])

    op.create_table(
        "paper_validation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_validation_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["paper_validation_plan_id"], ["paper_validation_plans.id"]),
    )
    op.create_index("ix_paper_validation_events_paper_validation_plan_id", "paper_validation_events", ["paper_validation_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_paper_validation_events_paper_validation_plan_id", table_name="paper_validation_events")
    op.drop_table("paper_validation_events")

    op.drop_index("ix_paper_validation_plans_status", table_name="paper_validation_plans")
    op.drop_index("ix_paper_validation_plans_strategy_config_id", table_name="paper_validation_plans")
    op.drop_index("ix_paper_validation_plans_backtest_run_id", table_name="paper_validation_plans")
    op.drop_index("ix_paper_validation_plans_baseline_candidate_id", table_name="paper_validation_plans")
    op.drop_table("paper_validation_plans")
```

### Key Patterns
- Use semantic revision IDs: `k6l7m8n9o0p1_add_mh16_paper_validation_plans`
- Include detailed docstring with revision info
- Set `down_revision` to link chain
- Create indexes for foreign keys and status fields
- Use `server_default=sa.text("now()")` for timestamp columns
- Reverse operations in `downgrade()` in reverse order of `upgrade()`
- Use `postgresql.UUID(as_uuid=True)` for UUID columns
- Use `postgresql.JSONB` for JSON fields

---

## 3. Pydantic Schema Patterns

**Location:** `apps/api/app/schemas/strategy_lab.py`

### Request Schema

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StrategyConfigCreateRequest(BaseModel):
    """Payload for creating a new strategy configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    strategy_type: str = Field(..., min_length=1, max_length=100)
    asset: str = Field(..., min_length=1, max_length=50)
    timeframe: str = Field(..., min_length=1, max_length=10)
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_settings: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
```

### Response Schema

```python
class StrategyConfigResponse(BaseModel):
    """Single strategy configuration."""

    id: UUID
    name: str
    strategy_type: str
    asset: str
    timeframe: str
    parameters: dict[str, Any]
    risk_settings: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### List Response Schema

```python
class StrategyConfigListResponse(BaseModel):
    """Paginated list of strategy configurations."""

    total: int
    items: list[StrategyConfigResponse]
```

### Complex Validation Example

```python
class PaperValidationPlanCreateRequest(BaseModel):
    """Create paper validation requirements from a baseline candidate."""

    baseline_candidate_id: str
    required_trades: int = Field(default=100, ge=1)
    minimum_days: int = Field(default=30, ge=1)
    target_profit_factor: float | None = Field(default=None, ge=0)
    max_drawdown_pct: float | None = None
    max_daily_loss_pct: float | None = None
    starting_paper_capital: float = Field(default=200000, gt=0)
    created_by: str | None = None
    review_notes: str | None = None
```

### With Pattern Validation

```python
class BaselineCandidateUpdateRequest(BaseModel):
    """Patch candidate status and review notes."""

    status: BaselineCandidateStatus | None = Field(
        default=None,
        pattern="^(watchlist_candidate|baseline_candidate|rejected|needs_more_testing)$",
    )
    review_notes: str | None = None
    reviewed_by: str | None = None
```

### Key Patterns
- Use `from __future__ import annotations` for forward references
- Include docstring describing purpose
- Use `Field(...)` for required fields, `Field(default=...)` for optional
- Use constraints: `min_length`, `max_length`, `ge`, `gt`, `pattern`
- Use type unions with `|` operator: `float | None`
- Use `dict[str, Any]` for flexible dictionaries
- Use `list[Type]` for arrays
- Add `model_config = {"from_attributes": True}` for ORM mapping
- Name request schemas with `*Request` suffix
- Name response schemas with `*Response` suffix
- Name list responses with `*ListResponse` suffix

---

## 4. Service Patterns

**Location:** `apps/api/app/services/paper_validation_service.py`

### Service Class Structure

```python
"""Paper validation gate service for MH-16/MH-17.

This service is intentionally isolated from live execution and broker flows.
It only tracks plan requirements/progress and deterministic pass/fail outcomes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.baseline_candidate import BaselineCandidate
from app.db.models.paper_validation_event import PaperValidationEvent
from app.db.models.paper_validation_evidence import PaperValidationEvidence
from app.db.models.paper_validation_plan import PaperValidationPlan
from app.schemas.strategy_lab import (
    PaperValidationEvidenceListResponse,
    PaperValidationEvidenceResponse,
    PaperValidationEventResponse,
    PaperValidationManualEvidenceRequest,
    PaperValidationPlanActionRequest,
    PaperValidationPlanCreateRequest,
    PaperValidationPlanListResponse,
    PaperValidationPlanResponse,
    PaperValidationPlanUpdateRequest,
    PaperValidationProgressResponse,
    PaperValidationReconcileRequest,
    PaperValidationReconcileResponse,
)

if TYPE_CHECKING:
    from app.schemas.strategy_lab import (
        PaperValidationDashboardResponse,
        PaperValidationReadinessResponse,
    )


class PaperValidationError(Exception):
    """Controlled paper validation failures."""


def _to_float(value: Any) -> float | None:
    """Helper to safely convert to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    """Helper to safely convert to int."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class PaperValidationService:
    """Application service for MH-16 paper validation plans."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _add_event(
        self,
        plan_id: uuid.UUID,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event for a validation plan."""
        self._session.add(
            PaperValidationEvent(
                paper_validation_plan_id=plan_id,
                event_type=event_type,
                message=message,
                payload=payload,
            )
        )

    def _compute_progress_from_evidence(
        self,
        plan: PaperValidationPlan,
        evidence_rows: list[PaperValidationEvidence],
    ) -> PaperValidationProgressResponse:
        """Compute progress metrics from included evidence records."""
        included = [e for e in evidence_rows if e.included_in_metrics]

        wins = sum(1 for e in included if e.result == "win")
        losses = sum(1 for e in included if e.result == "loss")
        breakeven = sum(1 for e in included if e.result == "breakeven")
        total_paper_trades = wins + losses + breakeven

        # ... computation logic
        
        return PaperValidationProgressResponse(
            total_paper_trades=total_paper_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            days_active=days_active,
            progress_trades_pct=progress_trades_pct,
            progress_days_pct=progress_days_pct,
            pass_fail_status=pass_fail_status,
            reasons=reasons,
        )
```

### Key Patterns
- Add module docstring explaining service purpose and scope
- Create custom exception class: `class ServiceNameError(Exception)`
- Use private session: `self._session`
- Use private helper methods with `_` prefix: `_to_float()`, `_now()`
- Accept `Session` in `__init__(self, session: Session)`
- Type hints with `|` operator: `value | None`
- Use `uuid.UUID` for ID parameters
- Return Pydantic response models
- Log events/changes to audit tables
- Raise custom exception on validation failures

---

## 5. Route Patterns (FastAPI)

**Location:** `apps/api/app/api/routes/strategy_lab.py`, `paper_validation.py`

### Route Setup

```python
"""Strategy Lab API routes — MH-06 data contracts + MH-07 replay.

Available endpoints:
    POST   /strategy-lab/configs
    GET    /strategy-lab/configs
    GET    /strategy-lab/configs/{config_id}
    POST   /strategy-lab/backtests
    GET    /strategy-lab/backtests
    GET    /strategy-lab/backtests/{backtest_id}
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.strategy_lab import (
    BacktestReplayRequest,
    BacktestReplayResponse,
    BacktestRunCreateRequest,
    BacktestRunListResponse,
    BacktestRunResponse,
    # ... more imports
)
from app.services.strategy_lab_service import StrategyLabService
from app.services.historical_replay_service import HistoricalReplayService, ReplayError

router = APIRouter(prefix="/strategy-lab", tags=["strategy_lab"])


def _svc(session: Session = Depends(get_db_session)) -> StrategyLabService:
    return StrategyLabService(session)


def _replay_svc(session: Session = Depends(get_db_session)) -> HistoricalReplayService:
    return HistoricalReplayService(session)
```

### POST Route (Create)

```python
@router.post(
    "/configs",
    response_model=StrategyConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_config(
    body: StrategyConfigCreateRequest,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyConfigResponse:
    config = svc.create_config(
        name=body.name,
        strategy_type=body.strategy_type,
        asset=body.asset,
        timeframe=body.timeframe,
        parameters=body.parameters,
        risk_settings=body.risk_settings,
        enabled=body.enabled,
    )
    return StrategyConfigResponse.model_validate(config)
```

### GET List Route

```python
@router.get("/configs", response_model=StrategyConfigListResponse)
def list_configs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: StrategyLabService = Depends(_svc),
) -> StrategyConfigListResponse:
    total, items = svc.list_configs(limit=limit, offset=offset)
    return StrategyConfigListResponse(
        total=total,
        items=[StrategyConfigResponse.model_validate(c) for c in items],
    )
```

### GET Detail Route

```python
@router.get("/configs/{config_id}", response_model=StrategyConfigResponse)
def get_config(
    config_id: UUID,
    svc: StrategyLabService = Depends(_svc),
) -> StrategyConfigResponse:
    config = svc.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Strategy config not found")
    return StrategyConfigResponse.model_validate(config)
```

### Sub-resource Route

```python
@router.get("/backtests/{backtest_id}/trades", response_model=MockTradeListResponse)
def list_trades(
    backtest_id: UUID,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: StrategyLabService = Depends(_svc),
) -> MockTradeListResponse:
    _assert_run_exists(backtest_id, svc)
    total, items = svc.list_trades(backtest_id, limit=limit, offset=offset)
    return MockTradeListResponse(total=total, items=items)  # type: ignore[arg-type]
```

### Exception Handling Route

```python
@router.post("/plans", response_model=PaperValidationPlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    body: PaperValidationPlanCreateRequest,
    svc: PaperValidationService = Depends(_svc),
) -> PaperValidationPlanResponse:
    try:
        return svc.create_plan(body)
    except PaperValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

### Key Patterns
- Create router with `prefix` and `tags`: `APIRouter(prefix="/strategy-lab", tags=["strategy_lab"])`
- Create dependency functions for each service: `def _svc(...):`
- Use `response_model` and `status_code` decorators
- Extract fields from request body: `body.field_name`
- Use `.model_validate()` to convert ORM to Pydantic
- Use `HTTPException` with appropriate status codes
- Wrap service calls in try-catch for custom exceptions
- Use Query parameters with validation: `Query(default, ge=1, le=500)`
- Path parameters are typed: `config_id: UUID`
- Use `type: ignore[arg-type]` sparingly for deliberate type allowances

---

## 6. Frontend API Client Patterns (TypeScript)

**Location:** `apps/web/lib/api/strategyLab.ts`, `core.ts`

### Core API Request

```typescript
// apps/web/lib/api/core.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export type ExecutionJournalSubscriber = () => void;

export const journalSubscribers = new Set<ExecutionJournalSubscriber>();

export function notifyJournalSubscribers() {
  for (const subscriber of journalSubscribers) {
    subscriber();
  }
}

export async function apiRequest<TResponse>(path: string, init: RequestInit): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`API request failed with status ${response.status}${message ? `: ${message}` : ""}`);
  }

  return (await response.json()) as TResponse;
}
```

### POST Request Function

```typescript
export async function createStrategyConfig(
  request: StrategyConfigCreateRequest,
): Promise<StrategyConfig> {
  return apiRequest<StrategyConfig>("/strategy-lab/configs", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
```

### GET List Request

```typescript
export async function getStrategyConfigs(): Promise<StrategyConfigListResponse> {
  return apiRequest<StrategyConfigListResponse>("/strategy-lab/configs", {
    method: "GET",
  });
}
```

### GET Detail Request

```typescript
export async function getStrategyConfig(configId: string): Promise<StrategyConfig> {
  return apiRequest<StrategyConfig>(`/strategy-lab/configs/${configId}`, {
    method: "GET",
  });
}
```

### Request with Parameters

```typescript
export async function getBaselineCandidates(
  params?: { status?: string; backtest_run_id?: string },
): Promise<BaselineCandidateListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.backtest_run_id) query.set("backtest_run_id", params.backtest_run_id);
  const suffix = query.toString() ? `?${query.toString()}` : "";

  return apiRequest<BaselineCandidateListResponse>(`/baseline-candidates${suffix}`, {
    method: "GET",
  });
}
```

### Key Patterns
- Generic type parameter: `apiRequest<TResponse>(path, init)`
- Use `process.env.NEXT_PUBLIC_*` for environment variables
- Add `cache: "no-store"` for data consistency
- Merge headers: `...(init.headers ?? {})`
- Use `JSON.stringify()` for request bodies
- Export named functions for each endpoint
- Use `string` for IDs in parameter types (for flexibility)
- Use `URLSearchParams` for query parameters
- Handle errors with descriptive messages
- Use generics: `Promise<TypeResponse>`

---

## 7. Frontend Types Structure

**Location:** `apps/web/lib/types.ts`

### Type Aliases

```typescript
export type Timeframe = "15m" | "1h" | "4h" | "1d";

export type ExecutionMode = "paper" | "confirm_live" | "auto_live";

export type SignalDirection = "long" | "short" | "flat";

export type SignalRegime =
  | "trend"
  | "range"
  | "breakout"
  | "high_volatility"
  | "low_volatility"
  | "risk_on"
  | "risk_off";

export type HorizonLabel = "intraday" | "1_3_days" | "3_10_days";

export type CatalystType =
  | "none"
  | "macro"
  | "earnings"
  | "sector_news"
  | "commodity_move"
  | "central_bank"
  | "geopolitics";

export type ResearchJobType = "historical_import" | "quality_recalculate";

export type ResearchJobStatus = "queued" | "running" | "completed" | "partial" | "failed" | "cancelled";
```

### Response Interfaces

```typescript
export interface SignalResponse {
  asset: string;
  timeframe: Timeframe;
  direction: SignalDirection;
  regime: SignalRegime;
  setup_type: SignalSetupType;
  entry_zone: [number, number];
  stop_price: number;
  target_price: number;
  confidence: number;
  horizon_label: HorizonLabel;
  catalyst_type: CatalystType;
  catalyst_score: number;
  catalyst_summary: string;
  thesis: string;
  invalidators: string[];
  signal_score: number;
  should_trade: boolean;
}

export interface HealthStatusResponse {
  status: string;
}

export interface StrategyConfig {
  id: string;
  name: string;
  strategy_type: string;
  asset: string;
  timeframe: string;
  parameters: Record<string, unknown>;
  risk_settings: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface StrategyConfigCreateRequest {
  name: string;
  strategy_type: string;
  asset: string;
  timeframe: string;
  parameters: Record<string, unknown>;
  risk_settings: Record<string, unknown>;
  enabled: boolean;
}

export interface StrategyConfigListResponse {
  total: int;
  items: StrategyConfig[];
}
```

### Complex Response Interfaces

```typescript
export interface PaperExecutionResponse {
  execution_id: string;
  status: string;
  asset: string;
  timeframe: string;
  side: string;
  qty: number;
  notional: number;
  stop_price: number;
  target_price: number;
  fill_price: number;
  reason?: string | null;
}

export interface PositionResponse {
  id: string;
  asset_id: string;
  asset_symbol: string;
  signal_id: string | null;
  status: string;
  side: string;
  avg_entry_price: number | null;
  current_price: number | null;
  stop_price: number | null;
  target_price: number | null;
  qty: number | null;
  opened_at: string | null;
  closed_at: string | null;
  close_reason: string | null;
  realized_pnl: number | null;
  unrealized_pnl: number | null;
}

export interface ResearchJob {
  id: string;
  job_type: ResearchJobType;
  status: ResearchJobStatus;
  requested_by: string | null;
  request_payload: Record<string, unknown>;
  result_payload: Record<string, unknown> | null;
  progress_current: number;
  progress_total: number;
  progress_message: string | null;
  error_message: string | null;
  retry_of_job_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}
```

### Key Patterns
- Use `type` for discriminated unions: `type Timeframe = "15m" | "1h" | "4h" | "1d"`
- Use `interface` for object shapes
- Use `Record<string, unknown>` for flexible objects
- Use `string | null` for nullable strings (not `string | undefined`)
- Use `SomeType[]` instead of `Array<SomeType>`
- Suffix response interfaces with `Response`
- Suffix request interfaces with `Request`
- Suffix list responses with `ListResponse`
- Use `number | null` for nullable numbers
- Export all types for frontend usage

---

## 8. Frontend Component Patterns (React/Next.js)

**Location:** `apps/web/app/strategy-lab/page.tsx`

### Page Component Setup

```typescript
"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createBacktestRun,
  createStrategyConfig,
  getBacktestDrawdowns,
  getBacktestEquityCurve,
  getBacktestResults,
  getBacktestRun,
  getBacktestRuns,
  getBacktestTrades,
  getStrategyComparisonDetail,
  getStrategyComparisonHistory,
  getStrategyConfigs,
  labelStrategyComparison,
  replayBacktest,
  runStrategyComparison,
  generateAIBacktestReport,
  getAIBacktestReports,
  createBaselineCandidate,
  getBaselineCandidates,
  updateBaselineCandidate,
  rejectBaselineCandidate,
  createPaperValidationPlan,
  getPaperValidationPlans,
  startPaperValidationPlan,
  stopPaperValidationPlan,
  recalculatePaperValidationPlan,
  getPaperValidationEvidence,
  addManualPaperValidationEvidence,
  excludePaperValidationEvidence,
  includePaperValidationEvidence,
  reconcilePaperValidationPlan,
  getPaperValidationDashboard,
  getPaperValidationReadiness,
} from "../../lib/api";
import type {
  AIBacktestReport,
  AIReportConfigItem,
  AIBacktestReportRequest,
  BaselineCandidate,
  BaselineCandidateStatus,
  PaperValidationEvidence,
  PaperValidationEvidenceListResponse,
  PaperValidationManualEvidenceRequest,
  PaperValidationPlan,
  PaperValidationReconcileResponse,
  PaperValidationStatus,
  PaperValidationDashboardResponse,
  PaperValidationReadinessResponse,
  BacktestReplayResponse,
  BacktestRun,
  DrawdownPeriod,
  EquityCurvePoint,
  MockTrade,
  StrategyComparisonDetailResponse,
  StrategyComparisonHistoryRow,
  StrategyComparisonResponse,
  StrategyComparisonRow,
  StrategyConfig,
  StrategyResult,
} from "../../lib/types";
import styles from "../../styles/pages/strategy-lab.module.css";

type LoadState = "loading" | "ready" | "error";

type SummaryShape = {
  total_candles_loaded?: number;
  total_mock_trades?: number;
  win_rate?: number | null;
  profit_factor?: number | null;
  total_return_pct?: number | null;
  max_drawdown_pct?: number | null;
  warnings?: string[];
  message?: string;
};
```

### Utility Functions in Components

```typescript
function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${value.toFixed(2)}%`;
}

function normalizeConfidence(value: number | null | undefined): number | null {
  if (value == null || Number.isNaN(value)) return null;
  const scaled = value >= 0 && value <= 1 ? value * 100 : value;
  return Math.max(0, Math.min(100, scaled));
}

function isAIConfigObject(item: string | AIReportConfigItem): item is AIReportConfigItem {
  return typeof item === "object" && item !== null;
}

function getStatusTone(status: string | null | undefined): string {
  if (!status) return styles.statusUnknown;
  if (status === "completed") return styles.statusOk;
  if (status === "passed") return styles.statusOk;
  if (status === "failed") return styles.statusBad;
  if (status === "stopped") return styles.statusBad;
  if (status === "running") return styles.statusWarn;
  if (status === "active") return styles.statusWarn;
  if (status === "pending") return styles.statusWarn;
  return styles.statusUnknown;
}

function buildEquityPolyline(points: EquityCurvePoint[]): string {
  if (points.length === 0) return "";
  const width = 780;
  const height = 220;
  const pad = 16;
  const values = points.map((p) => p.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  return points
    .map((point, index) => {
      const x =
        points.length === 1
          ? width / 2
          : pad + (index / (points.length - 1)) * (width - pad * 2);
      const y = height - pad - ((point.equity - min) / span) * (height - pad * 2);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}
```

### Key Patterns
- Use `"use client"` directive at top for client components
- Import API functions from `lib/api`
- Import types with `type` keyword: `import type { Type }`
- Import styles with full path: `import styles from "../../styles/pages/strategy-lab.module.css"`
- Define local type aliases for component-specific types
- Create utility functions for formatting, transformation, and validation
- Use `| null | undefined` for nullable values (defensive coding)
- Use type guards: `item is AIReportConfigItem`
- Use `Record<string, unknown>` for flexible data
- Return `"-"` as default placeholder for missing values
- Use `toLocaleString()` for number formatting
- Use `.toFixed(n)` for decimal precision
- Use `Number.isNaN()` for null-safe checks
- Separate formatting logic into pure functions
- Use className mapping objects from CSS modules

---

## Quick Reference: Import Organization

### Backend (Python)

```python
from __future__ import annotations

# Standard library
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

# SQLAlchemy
from sqlalchemy import DateTime, String, Text, and_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

# FastAPI
from fastapi import APIRouter, Depends, HTTPException, Query, status

# Local
from app.db.base import Base
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import get_db_session
from app.schemas.strategy_lab import ...
from app.services.paper_validation_service import ...

if TYPE_CHECKING:
    from app.schemas.strategy_lab import ...
```

### Frontend (TypeScript)

```typescript
"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createStrategyConfig,
  getStrategyConfigs,
  // ... API functions
} from "../../lib/api";
import type {
  StrategyConfig,
  StrategyConfigListResponse,
  // ... Types
} from "../../lib/types";
import styles from "../../styles/pages/strategy-lab.module.css";

type LocalType = "value1" | "value2";
```

---

## Summary: Style Checklist

- ✅ DB models: inherit `UUIDPrimaryKeyMixin`, `TimestampMixin`, `Base`
- ✅ DB models: use `Mapped[type]` with `mapped_column()`
- ✅ Alembic: use semantic revision IDs, create indexes
- ✅ Schemas: add docstrings, use `Field()`, include `model_config`
- ✅ Services: use private session, raise custom exceptions
- ✅ Routes: use dependency injection, `model_validate()`, exception handling
- ✅ API client: generic types, query parameters, error handling
- ✅ Frontend types: type aliases, interfaces, `Record<string, unknown>`
- ✅ Components: `"use client"`, utility functions, defensive null checks
- ✅ All files: `from __future__ import annotations` at top
- ✅ All files: comprehensive module docstrings
