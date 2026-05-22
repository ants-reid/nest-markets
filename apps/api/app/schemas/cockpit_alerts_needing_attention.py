from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CockpitAttentionSummarySchema(BaseModel):
    headline: str
    total_items: int
    high_priority: int
    medium_priority: int
    low_priority: int
    unknown_priority: int
    active_alerts: int
    unresolved_incidents: int
    monitor_degraded: int
    stale_data: int
    risk_attention: int
    trading_halt: int
    missing_context: int


class CockpitAttentionItemSchema(BaseModel):
    id: str
    source: Literal[
        "alert",
        "incident",
        "monitor",
        "risk",
        "trading_halt",
        "notification",
        "paper",
        "unknown",
    ]
    title: str
    message: str
    priority: Literal["high", "medium", "low", "unknown"]
    status: str
    detected_at: str | None
    attention_type: Literal[
        "active_alert",
        "unresolved_incident",
        "monitor_degraded",
        "stale_data",
        "risk_attention",
        "trading_halt",
        "missing_context",
    ]
    evidence: list[str]
    missing_data: list[str]
    recommended_review_action: str
    is_actionable: Literal[False]


class CockpitAttentionGroupSchema(BaseModel):
    group: str
    count: int
    item_ids: list[str]


class CockpitAlertsNeedingAttentionResponseSchema(BaseModel):
    generated_at: str
    mode: Literal["paper"]
    summary: CockpitAttentionSummarySchema
    attention_items: list[CockpitAttentionItemSchema]
    grouped_by_priority: list[CockpitAttentionGroupSchema]
    grouped_by_source: list[CockpitAttentionGroupSchema]
    monitor_notes: list[str]
    risk_notes: list[str]
    limitations: list[str]
    recommended_review_actions: list[str]
