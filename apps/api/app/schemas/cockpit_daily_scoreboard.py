from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CockpitDailyScoreboardSummarySchema(BaseModel):
    headline: str
    day_status: Literal[
        "green_day",
        "red_day",
        "flat_day",
        "data_incomplete",
        "review_required",
        "monitor_attention",
        "unknown",
    ]
    trades_opened_today: int
    trades_closed_today: int
    open_positions_now: int


class CockpitDailyScoreboardPerformanceSchema(BaseModel):
    realized_pnl_today: float | None
    unrealized_pnl_snapshot: float | None
    net_pnl_today: float | None
    win_count: int | None
    loss_count: int | None
    flat_count: int | None
    unknown_count: int


class CockpitDailyScoreboardActivitySchema(BaseModel):
    trades_opened_today: int
    trades_closed_today: int
    open_positions_now: int


class CockpitDailyScoreboardOpenPositionsSchema(BaseModel):
    count: int
    long_count: int
    short_count: int


class CockpitDailyScoreboardClosedPositionsSchema(BaseModel):
    count: int
    wins: int | None
    losses: int | None
    flat: int | None
    unknown: int


class CockpitDailyScoreboardContributorSchema(BaseModel):
    symbol: str
    asset_id: str | None = None
    asset_name: str | None = None
    asset_detail_path: str | None = None
    has_asset_context: bool = False
    realized_pnl: float | None
    contribution_label: Literal["positive", "negative", "flat", "unknown"]
    evidence: list[str]


class CockpitDailyScoreboardTopContributorsSchema(BaseModel):
    count: int
    items: list[CockpitDailyScoreboardContributorSchema]


class CockpitDailyScoreboardNoteSchema(BaseModel):
    label: Literal[
        "green_day",
        "red_day",
        "flat_day",
        "data_incomplete",
        "review_required",
        "monitor_attention",
        "unknown",
    ]
    title: str
    detail: str
    severity: str
    created_at: str | None


class CockpitDailyScoreboardResponseSchema(BaseModel):
    report_date: str
    generated_at: str
    mode: Literal["paper"]
    summary: CockpitDailyScoreboardSummarySchema
    performance: CockpitDailyScoreboardPerformanceSchema
    activity: CockpitDailyScoreboardActivitySchema
    open_positions: CockpitDailyScoreboardOpenPositionsSchema
    closed_positions: CockpitDailyScoreboardClosedPositionsSchema
    top_contributors: CockpitDailyScoreboardTopContributorsSchema
    risk_and_monitor_notes: list[CockpitDailyScoreboardNoteSchema]
    review_priorities: list[str]
    limitations: list[str]
