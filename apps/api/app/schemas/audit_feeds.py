"""Read-only cockpit audit feed response schemas.

Typed envelopes for the four sibling cockpit audit feeds that previously
returned bare ``dict[str, Any]``:

* ``GET /risk-decisions/recent``
* ``GET /news-in-decision-log/recent``
* ``GET /llm-logs/recent``
* ``GET /monitor/worker-run-log/overview``

Fields mirror the existing ``_serialize`` output of each route so the
existing frontend client modules and Playwright fixtures keep working
unchanged.

Drift-lock guarantee:
* Read-only schemas; no behaviour change.
* No secret-like field names; previews/payload strings are already
  length-capped + control-stripped at write/serialize time.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# /risk-decisions/recent
# ---------------------------------------------------------------------------


class RiskDecisionAuditRowSchema(BaseModel):
    """One row of the deterministic risk-engine decision audit feed."""

    id: str
    created_at: Optional[str] = None
    timestamp: Optional[str] = None
    signal_id: Optional[str] = None
    approved: bool
    blocking_rule: Optional[str] = None
    block_reason_code: Optional[str] = None
    risk_profile_id: Optional[str] = None
    position_risk_pct: Optional[float] = None
    notional_allowed: Optional[float] = None
    correlation_bucket: Optional[str] = None
    spread_ok: Optional[bool] = None
    session_ok: Optional[bool] = None
    drawdown_ok: Optional[bool] = None
    cooldown_ok: Optional[bool] = None
    kill_switch_active: Optional[bool] = None
    blocked_reasons_json: Optional[Any] = None


class RiskDecisionAuditFiltersSchema(BaseModel):
    """Echo of active filters on the risk-decisions audit feed."""

    approved: Optional[str] = None
    signal_id: Optional[str] = None
    block_reason_code: Optional[str] = None


class RiskDecisionAuditResponseSchema(BaseModel):
    """Envelope returned by ``GET /risk-decisions/recent``."""

    count: int
    limit: int
    filters: RiskDecisionAuditFiltersSchema
    advisory: str
    items: list[RiskDecisionAuditRowSchema]


# ---------------------------------------------------------------------------
# /news-in-decision-log/recent
# ---------------------------------------------------------------------------


class NewsInDecisionLogAuditRowSchema(BaseModel):
    """One row of the news-in-decision audit log."""

    id: str
    created_at: Optional[str] = None
    decision_kind: str
    decision_id: Optional[str] = None
    signal_id: Optional[str] = None
    llm_request_log_id: Optional[str] = None
    news_article_id: Optional[str] = None
    news_item_id: Optional[str] = None
    evidence_class: str
    headline_snapshot: Optional[str] = None
    source_snapshot: Optional[str] = None
    url_snapshot: Optional[str] = None
    published_at_snapshot: Optional[str] = None
    context_json: Optional[dict[str, Any]] = None


class NewsInDecisionLogAuditFiltersSchema(BaseModel):
    """Echo of active filters on the news-in-decision audit feed."""

    decision_kind: Optional[str] = None
    signal_id: Optional[str] = None
    news_article_id: Optional[str] = None


class NewsInDecisionLogAuditResponseSchema(BaseModel):
    """Envelope returned by ``GET /news-in-decision-log/recent``."""

    count: int
    limit: int
    filters: NewsInDecisionLogAuditFiltersSchema
    advisory: str
    items: list[NewsInDecisionLogAuditRowSchema]


# ---------------------------------------------------------------------------
# /llm-logs/recent
# ---------------------------------------------------------------------------


class LlmLogAuditRowSchema(BaseModel):
    """One row of the redacted LLM round-trip audit feed.

    All preview/payload fields are already length-capped and
    control-stripped at write time by ``llm_request_log_sink``; the
    route additionally re-caps before serialization.
    """

    id: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    provider: str
    model_requested: str
    model_returned: Optional[str] = None
    system_prompt_hash: Optional[str] = None
    user_prompt_hash: Optional[str] = None
    system_prompt_preview: Optional[str] = None
    user_prompt_preview: Optional[str] = None
    prompt_version_id: Optional[str] = None
    stop_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    error_class: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    response_payload_preview: Optional[str] = None


class LlmLogAuditFiltersSchema(BaseModel):
    """Echo of active filters on the LLM logs audit feed."""

    provider: Optional[str] = None
    correlation_id: Optional[str] = None
    only_errors: bool


class LlmLogAuditResponseSchema(BaseModel):
    """Envelope returned by ``GET /llm-logs/recent``."""

    count: int
    limit: int
    filters: LlmLogAuditFiltersSchema
    items: list[LlmLogAuditRowSchema]


# ---------------------------------------------------------------------------
# /monitor/worker-run-log/overview
# ---------------------------------------------------------------------------


class WorkerRunLogEntrySchema(BaseModel):
    """One persisted auto-paper worker run entry (mirrors WorkerRunEntry)."""

    worker_name: str
    status: str
    message: str
    started_at: str
    finished_at: str
    source: str
    outcome_counts: Optional[dict[str, int]] = None


class WorkerRunLogRetentionSchema(BaseModel):
    """Retention metadata for the file-backed worker run log."""

    storage_backend: str
    trim_on_append: bool
    max_entries: int
    current_entry_count: int
    entries_remaining: int
    utilization_pct: float
    warning_threshold_pct: float
    near_capacity: bool
    retention_status: str
    retention_warning: Optional[str] = None
    retained_span_hours: Optional[float] = None
    average_entries_per_day: Optional[float] = None
    estimated_days_until_capacity: Optional[float] = None
    retention_trend_status: str
    log_exists: bool
    oldest_started_at: Optional[str] = None
    latest_started_at: Optional[str] = None


class WorkerRunLogTotalsSchema(BaseModel):
    """Aggregate counts for the entries in the current overview window."""

    returned: int
    by_status: dict[str, int]
    by_source: dict[str, int]


class WorkerRunLogOverviewResponseSchema(BaseModel):
    """Envelope returned by ``GET /monitor/worker-run-log/overview``."""

    advisory: str
    limit: int
    retention: WorkerRunLogRetentionSchema
    totals: WorkerRunLogTotalsSchema
    entries: list[WorkerRunLogEntrySchema]
