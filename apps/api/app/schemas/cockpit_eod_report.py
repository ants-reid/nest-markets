from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CockpitEodSummarySchema(BaseModel):
    headline: str
    opened_today: int
    closed_today: int
    open_positions_now: int
    alerts_needing_attention: int
    lessons_available: int


class CockpitEodPnlSchema(BaseModel):
    realized_day: float | None
    unrealized_snapshot: float | None
    realized_basis: str
    unrealized_basis: str


class CockpitEodOpenPositionItemSchema(BaseModel):
    asset_symbol: str
    side: str
    qty: float | None
    opened_at: str | None
    unrealized_pnl: float | None


class CockpitEodTradeItemSchema(BaseModel):
    asset_symbol: str
    side: str
    opened_at: str | None
    closed_at: str | None
    realized_pnl: float | None
    close_reason: str | None


class CockpitEodClosedPositionsSchema(BaseModel):
    count: int
    wins: int | None
    losses: int | None
    flat: int | None
    unknown: int
    best_trade: CockpitEodTradeItemSchema | None
    worst_trade: CockpitEodTradeItemSchema | None
    items: list[CockpitEodTradeItemSchema]


class CockpitEodPaperActivitySchema(BaseModel):
    opened_today: int
    closed_today: int
    current_open_positions: int


class CockpitEodIncidentItemSchema(BaseModel):
    severity: str
    code: str
    title: str
    source: str
    created_at: str | None
    detail: str | None


class CockpitEodMonitorNoteSchema(BaseModel):
    title: str
    detail: str
    severity: str
    created_at: str | None


class CockpitEodLessonSchema(BaseModel):
    title: str
    detail: str
    evidence_count: int


class CockpitEodOpenPositionsSchema(BaseModel):
    count: int
    items: list[CockpitEodOpenPositionItemSchema]


class CockpitEodReportResponseSchema(BaseModel):
    report_date: str
    generated_at: str
    mode: Literal["paper"]
    summary: CockpitEodSummarySchema
    paper_activity: CockpitEodPaperActivitySchema
    pnl: CockpitEodPnlSchema
    open_positions: CockpitEodOpenPositionsSchema
    closed_positions: CockpitEodClosedPositionsSchema
    alerts_or_incidents: list[CockpitEodIncidentItemSchema]
    monitor_notes: list[CockpitEodMonitorNoteSchema]
    lessons: list[CockpitEodLessonSchema]
    recommended_actions: list[str]
    limitations: list[str]