"""Schemas for the MH-38 risk-limit foundation."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _has_any_limit(values: dict[str, Any]) -> bool:
    limit_fields = {
        "max_order_notional",
        "daily_loss_limit_amount",
        "daily_loss_limit_pct",
        "max_open_positions",
        "max_total_exposure",
        "max_symbol_exposure",
        "max_trades_per_day",
        "min_cash_buffer",
    }
    return any(values.get(field) is not None for field in limit_fields)


class RiskLimitConfigBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str = Field(default="global")
    trading_mode: str = Field(default="paper")
    max_order_notional: float | None = Field(default=None, gt=0)
    daily_loss_limit_amount: float | None = Field(default=None, gt=0)
    daily_loss_limit_pct: float | None = Field(default=None, gt=0)
    max_open_positions: int | None = Field(default=None, gt=0)
    max_total_exposure: float | None = Field(default=None, gt=0)
    max_symbol_exposure: float | None = Field(default=None, gt=0)
    max_trades_per_day: int | None = Field(default=None, gt=0)
    min_cash_buffer: float | None = Field(default=None, gt=0)
    is_active: bool = True
    notes: str | None = None


class RiskLimitConfigCreateRequest(RiskLimitConfigBase):
    @model_validator(mode="after")
    def validate_has_limit(self) -> "RiskLimitConfigCreateRequest":
        if not _has_any_limit(self.model_dump()):
            raise ValueError("At least one risk limit field must be supplied.")
        return self


class RiskLimitConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str | None = None
    trading_mode: str | None = None
    max_order_notional: float | None = Field(default=None, gt=0)
    daily_loss_limit_amount: float | None = Field(default=None, gt=0)
    daily_loss_limit_pct: float | None = Field(default=None, gt=0)
    max_open_positions: int | None = Field(default=None, gt=0)
    max_total_exposure: float | None = Field(default=None, gt=0)
    max_symbol_exposure: float | None = Field(default=None, gt=0)
    max_trades_per_day: int | None = Field(default=None, gt=0)
    min_cash_buffer: float | None = Field(default=None, gt=0)
    is_active: bool | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_has_limit(self) -> "RiskLimitConfigUpdateRequest":
        data = self.model_dump(exclude_unset=True)
        if not data:
            raise ValueError("At least one field must be supplied for update.")
        non_limit_keys = {"scope", "trading_mode", "is_active", "notes"}
        if all(key in non_limit_keys for key in data):
            raise ValueError("At least one risk limit field must be supplied.")
        return self


class RiskLimitConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: str
    trading_mode: str
    max_order_notional: float | None
    daily_loss_limit_amount: float | None
    daily_loss_limit_pct: float | None
    max_open_positions: int | None
    max_total_exposure: float | None
    max_symbol_exposure: float | None
    max_trades_per_day: int | None
    min_cash_buffer: float | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RiskLimitViolation(BaseModel):
    code: str
    message: str
    actual_value: float | int | None = None
    limit_value: float | int | None = None


class RiskLimitCheckResult(BaseModel):
    allowed: bool
    enforcement_enabled: bool
    trading_mode: str
    evaluated_notional: float | None = None
    configured_limit_count: int
    violations: list[RiskLimitViolation]
    note: str


class RiskLimitStatusResponse(BaseModel):
    enforcement_enabled: bool
    trading_mode: str
    active_config: RiskLimitConfigResponse | None = None
    configured_limits: dict[str, float | int]
    missing_limits: list[str]
    has_max_order_notional: bool
    has_daily_loss_limit: bool
    has_max_open_positions: bool
    has_max_total_exposure: bool
    risk_limits_configured: bool
    note: str


class RiskLimitEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    side: str
    quantity: float = Field(gt=0)
    estimated_price: float | None = Field(default=None, gt=0)
    estimated_notional: float | None = Field(default=None, gt=0)
    trading_mode: str = "paper"
    current_total_exposure: float | None = Field(default=None, ge=0)
    current_symbol_exposure: float | None = Field(default=None, ge=0)
    current_open_positions: int | None = Field(default=None, ge=0)
    trades_today: int | None = Field(default=None, ge=0)
    available_cash: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_notional_source(self) -> "RiskLimitEvaluateRequest":
        if self.estimated_notional is None:
            if self.estimated_price is None:
                raise ValueError("estimated_price or estimated_notional must be supplied.")
            self.estimated_notional = self.quantity * self.estimated_price
        return self