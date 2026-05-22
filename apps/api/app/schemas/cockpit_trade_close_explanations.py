from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CockpitTradeCloseSummarySchema(BaseModel):
    headline: str
    total_closed_trades: int
    known_close_labels: int
    unknown_close_labels: int
    profitable_trades: int
    losing_trades: int
    flat_trades: int
    setup_matched: int
    setup_mismatched: int
    setup_unknown: int


class CockpitTradeCloseExplanationSchema(BaseModel):
    id: str
    paper_order_id: str | None
    position_id: str | None
    symbol: str
    asset_id: str | None = None
    asset_name: str | None = None
    asset_detail_path: str | None = None
    has_asset_context: bool = False
    opened_at: str | None
    closed_at: str | None
    status: str
    close_label: Literal[
        "target_hit",
        "stop_hit",
        "manual_close",
        "timeout_or_stale",
        "validation_close",
        "risk_close",
        "unknown",
    ]
    close_reason: str | None
    result_summary: str
    realized_pnl: float | None
    outcome_match: Literal["matched", "mismatched", "unknown"]
    evidence: list[str]
    missing_data: list[str]
    learning_note: str
    is_actionable: Literal[False]


class CockpitTradeCloseExplanationsResponseSchema(BaseModel):
    generated_at: str
    mode: Literal["paper"]
    summary: CockpitTradeCloseSummarySchema
    explanations: list[CockpitTradeCloseExplanationSchema]
    limitations: list[str]
    recommended_review_actions: list[str]
