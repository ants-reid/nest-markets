"""Pydantic request and response schemas for signal endpoints."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SignalResponse(BaseModel):
    """Typed API response schema for a structured signal."""

    model_config = ConfigDict(extra="forbid")

    signal_id: UUID | None = None
    asset: str
    timeframe: Literal["15m", "1h", "4h", "1d"]
    direction: Literal["long", "short", "flat"]
    regime: Literal[
        "trend",
        "range",
        "breakout",
        "high_volatility",
        "low_volatility",
        "risk_on",
        "risk_off",
    ]
    setup_type: Literal["trend_pullback", "breakout_confirmation", "news_continuation", "none"]
    entry_zone: tuple[float, float]
    stop_price: float = Field(ge=0)
    target_price: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    horizon_label: Literal["intraday", "1_3_days", "3_10_days"]
    catalyst_type: Literal[
        "none",
        "macro",
        "earnings",
        "sector_news",
        "commodity_move",
        "central_bank",
        "geopolitics",
    ]
    catalyst_score: float = Field(ge=0, le=1)
    catalyst_summary: str
    thesis: str
    invalidators: list[str]
    signal_score: float = Field(ge=0, le=100)
    should_trade: bool


class MockGenerateSignalRequest(BaseModel):
    """Request schema for safe mocked signal generation endpoint."""

    model_config = ConfigDict(extra="forbid")

    mocked_signal: SignalResponse | None = None
    asset: str = "EURUSD"
    timeframe: Literal["15m", "1h", "4h", "1d"] = "1h"
    latest_price: float = Field(default=0.0, ge=0)
