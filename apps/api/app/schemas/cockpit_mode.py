"""Schemas for the cockpit mode selector API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MODE_IDS = {
    "learning",
    "manual",
    "auto_paper",
    "assisted_live",
    "live",
    "auto_live",
}


class CockpitModeOptionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    status: Literal["active", "available", "locked"]
    selectable: bool
    locked: bool
    reason: str
    risk_note: str
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    safety_gates: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _MODE_IDS:
            raise ValueError(f"Unsupported cockpit mode: {value}")
        return normalized


class CockpitModeSafetyStateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    live_trading_enabled: bool
    auto_live_enabled: bool
    real_money_enabled: bool
    paper_order_submission_allowed: bool
    live_order_submission_allowed: bool
    auto_trading_allowed: bool
    emergency_stop_active: bool
    trading_mode: str
    execution_control: str
    arming_state: str
    reasons: list[str] = Field(default_factory=list)


class CockpitModeResponseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_mode: str
    selectable_modes: list[str] = Field(default_factory=list)
    locked_modes: list[str] = Field(default_factory=list)
    modes: list[CockpitModeOptionSchema] = Field(default_factory=list)
    global_safety_state: CockpitModeSafetyStateSchema
    live_trading_enabled: bool
    auto_live_enabled: bool
    real_money_enabled: bool
    notes: list[str] = Field(default_factory=list)

    @field_validator("current_mode")
    @classmethod
    def validate_current_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _MODE_IDS:
            raise ValueError(f"Unsupported cockpit mode: {value}")
        return normalized


class CockpitModeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_mode: str

    @field_validator("requested_mode")
    @classmethod
    def validate_requested_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _MODE_IDS:
            raise ValueError(f"Unsupported cockpit mode: {value}")
        return normalized