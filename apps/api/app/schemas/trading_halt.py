"""Schemas for the MH-39 trading halt foundation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HALT_TYPES = {"manual", "risk", "system", "broker", "unknown"}
_HALT_STATUSES = {"clear", "active", "resolved"}
_TRADING_MODES = {"paper", "live", "all"}


class TradingHaltCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    halt_type: str = Field(default="manual")
    scope: str = Field(default="global")
    trading_mode: str | None = None
    reason: str = Field(min_length=1)
    triggered_by: str | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("halt_type")
    @classmethod
    def validate_halt_type(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in _HALT_TYPES:
            raise ValueError(f"halt_type must be one of: {', '.join(sorted(_HALT_TYPES))}.")
        return normalized

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("scope is required.")
        return normalized

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lower()
        if normalized not in _TRADING_MODES:
            raise ValueError("trading_mode must be one of: all, live, paper.")
        return normalized

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason is required when creating an active trading halt.")
        return normalized


class TradingHaltResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolved_by: str | None = None
    resolution_notes: str | None = None


class TradingHaltResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    halt_type: str
    scope: str
    trading_mode: str | None
    reason: str | None
    triggered_by: str | None
    triggered_at: datetime
    resolved_by: str | None
    resolved_at: datetime | None
    resolution_notes: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in _HALT_STATUSES:
            raise ValueError("status must be one of: active, clear, resolved.")
        return normalized


class TradingHaltStatusResponse(BaseModel):
    emergency_stop_active: bool
    active_halt: TradingHaltResponse | None = None
    status: Literal["clear", "active"]
    blocked_reason: str | None = None
    enforcement_enabled: bool
    note: str


class TradingHaltListResponse(BaseModel):
    items: list[TradingHaltResponse]
    total: int
    limit: int
    offset: int
    status_filter: str | None = None