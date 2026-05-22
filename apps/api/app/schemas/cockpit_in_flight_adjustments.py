from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CockpitInFlightSummarySchema(BaseModel):
    headline: str
    total_items: int
    open_positions: int
    open_orders: int
    active_recommendations: int
    watch_only: int
    review_required: int
    high_attention: int


class CockpitInFlightItemSchema(BaseModel):
    id: str
    item_type: Literal["paper_position", "paper_order", "paper_recommendation", "unknown"]
    symbol: str
    asset_id: str | None = None
    asset_name: str | None = None
    asset_detail_path: str | None = None
    has_asset_context: bool = False
    status: str
    opened_at: str | None
    created_at: str | None
    current_state_summary: str
    attention_level: Literal["low", "medium", "high", "unknown"]
    adjustment_label: Literal[
        "watch_only",
        "review_required",
        "stale_data",
        "risk_attention",
        "missing_context",
        "monitor_issue",
        "unknown",
    ]
    reason: str
    evidence: list[str]
    missing_data: list[str]
    recommended_review_action: str
    is_actionable: Literal[False]


class CockpitInFlightNoteSchema(BaseModel):
    title: str
    detail: str
    severity: str
    created_at: str | None


class CockpitInFlightAdjustmentsResponseSchema(BaseModel):
    generated_at: str
    mode: Literal["paper"]
    summary: CockpitInFlightSummarySchema
    items: list[CockpitInFlightItemSchema]
    monitor_notes: list[CockpitInFlightNoteSchema]
    risk_notes: list[str]
    limitations: list[str]
    recommended_review_actions: list[str]
