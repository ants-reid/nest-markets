"""Backend-only risk-limit foundation for MH-38.

This service provides config, status, and evaluation primitives only.
It is intentionally not wired into broker submit or dry-run behavior yet.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import RiskLimitConfig
from app.schemas.risk_limits import (
    RiskLimitCheckResult,
    RiskLimitConfigCreateRequest,
    RiskLimitConfigResponse,
    RiskLimitConfigUpdateRequest,
    RiskLimitStatusResponse,
    RiskLimitViolation,
)

_LIMIT_FIELDS = {
    "max_order_notional",
    "daily_loss_limit_amount",
    "daily_loss_limit_pct",
    "max_open_positions",
    "max_total_exposure",
    "max_symbol_exposure",
    "max_trades_per_day",
    "min_cash_buffer",
}

_STATUS_LIMIT_FIELDS = [
    "max_order_notional",
    "daily_loss_limit_amount",
    "daily_loss_limit_pct",
    "max_open_positions",
    "max_total_exposure",
    "max_symbol_exposure",
    "max_trades_per_day",
    "min_cash_buffer",
]


class RiskLimitService:
    """Service for configuring and evaluating future risk limits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_active_config(self, trading_mode: str | None = None) -> RiskLimitConfig | None:
        query = self._session.query(RiskLimitConfig).filter(RiskLimitConfig.is_active.is_(True))

        if trading_mode:
            normalized_mode = trading_mode.lower()
            query = query.filter(RiskLimitConfig.trading_mode.in_([normalized_mode, "all"]))

        rows = query.order_by(RiskLimitConfig.updated_at.desc()).all()

        if not rows:
            return None

        if trading_mode:
            normalized_mode = trading_mode.lower()
            exact_match = next((row for row in rows if row.trading_mode == normalized_mode), None)
            if exact_match is not None:
                return exact_match

        global_match = next((row for row in rows if row.scope == "global"), None)
        return global_match or rows[0]

    def create_config(self, request: RiskLimitConfigCreateRequest) -> RiskLimitConfig:
        config = RiskLimitConfig(**self._to_model_data(request.model_dump()))
        self._session.add(config)
        self._session.commit()
        self._session.refresh(config)
        return config

    def update_config(self, config_id, request: RiskLimitConfigUpdateRequest) -> RiskLimitConfig | None:
        config = self._session.get(RiskLimitConfig, config_id)
        if config is None:
            return None

        for field, value in self._to_model_data(request.model_dump(exclude_unset=True)).items():
            setattr(config, field, value)

        self._session.commit()
        self._session.refresh(config)
        return config

    def list_configs(self) -> list[RiskLimitConfig]:
        return self._session.query(RiskLimitConfig).order_by(RiskLimitConfig.created_at.desc()).all()

    def get_status(self, trading_mode: str | None = None) -> RiskLimitStatusResponse:
        config = self.get_active_config(trading_mode=trading_mode)
        configured_limits: dict[str, float | int] = {}

        if config is not None:
            for field in _STATUS_LIMIT_FIELDS:
                value = getattr(config, field)
                if value is not None:
                    configured_limits[field] = self._normalize_scalar(value)

        missing_limits = [field for field in _STATUS_LIMIT_FIELDS if field not in configured_limits]

        return RiskLimitStatusResponse(
            enforcement_enabled=False,
            trading_mode=(trading_mode or (config.trading_mode if config else "paper")).lower(),
            active_config=RiskLimitConfigResponse.model_validate(config) if config is not None else None,
            configured_limits=configured_limits,
            missing_limits=missing_limits,
            has_max_order_notional="max_order_notional" in configured_limits,
            has_daily_loss_limit=(
                "daily_loss_limit_amount" in configured_limits or "daily_loss_limit_pct" in configured_limits
            ),
            has_max_open_positions="max_open_positions" in configured_limits,
            has_max_total_exposure="max_total_exposure" in configured_limits,
            risk_limits_configured=bool(configured_limits),
            note="Risk limits are configured for future enforcement but are not yet wired into broker submission.",
        )

    def evaluate_order_against_limits(self, order_context: dict) -> RiskLimitCheckResult:
        trading_mode = str(order_context.get("trading_mode") or "paper").lower()
        config = self.get_active_config(trading_mode=trading_mode)
        evaluated_notional = order_context.get("estimated_notional")
        violations: list[RiskLimitViolation] = []
        configured_limit_count = 0

        if config is not None and config.max_order_notional is not None:
            configured_limit_count += 1
            if evaluated_notional is not None and float(evaluated_notional) > float(config.max_order_notional):
                violations.append(
                    RiskLimitViolation(
                        code="max_order_notional_exceeded",
                        message="Estimated order notional exceeds configured max_order_notional.",
                        actual_value=float(evaluated_notional),
                        limit_value=float(config.max_order_notional),
                    )
                )

        if config is not None and config.max_total_exposure is not None:
            configured_limit_count += 1
            current_total_exposure = order_context.get("current_total_exposure")
            if current_total_exposure is not None and evaluated_notional is not None:
                projected = float(current_total_exposure) + float(evaluated_notional)
                if projected > float(config.max_total_exposure):
                    violations.append(
                        RiskLimitViolation(
                            code="max_total_exposure_exceeded",
                            message="Projected total exposure exceeds configured max_total_exposure.",
                            actual_value=projected,
                            limit_value=float(config.max_total_exposure),
                        )
                    )

        if config is not None and config.max_symbol_exposure is not None:
            configured_limit_count += 1
            current_symbol_exposure = order_context.get("current_symbol_exposure")
            if current_symbol_exposure is not None and evaluated_notional is not None:
                projected = float(current_symbol_exposure) + float(evaluated_notional)
                if projected > float(config.max_symbol_exposure):
                    violations.append(
                        RiskLimitViolation(
                            code="max_symbol_exposure_exceeded",
                            message="Projected symbol exposure exceeds configured max_symbol_exposure.",
                            actual_value=projected,
                            limit_value=float(config.max_symbol_exposure),
                        )
                    )

        if config is not None and config.max_open_positions is not None:
            configured_limit_count += 1
            current_open_positions = order_context.get("current_open_positions")
            if current_open_positions is not None and int(current_open_positions) + 1 > int(config.max_open_positions):
                violations.append(
                    RiskLimitViolation(
                        code="max_open_positions_exceeded",
                        message="Projected open positions exceed configured max_open_positions.",
                        actual_value=int(current_open_positions) + 1,
                        limit_value=int(config.max_open_positions),
                    )
                )

        if config is not None and config.max_trades_per_day is not None:
            configured_limit_count += 1
            trades_today = order_context.get("trades_today")
            if trades_today is not None and int(trades_today) + 1 > int(config.max_trades_per_day):
                violations.append(
                    RiskLimitViolation(
                        code="max_trades_per_day_exceeded",
                        message="Projected trades today exceed configured max_trades_per_day.",
                        actual_value=int(trades_today) + 1,
                        limit_value=int(config.max_trades_per_day),
                    )
                )

        if config is not None and config.min_cash_buffer is not None:
            configured_limit_count += 1
            available_cash = order_context.get("available_cash")
            if available_cash is not None and evaluated_notional is not None:
                remaining_cash = float(available_cash) - float(evaluated_notional)
                if remaining_cash < float(config.min_cash_buffer):
                    violations.append(
                        RiskLimitViolation(
                            code="min_cash_buffer_breached",
                            message="Projected available cash would breach configured min_cash_buffer.",
                            actual_value=remaining_cash,
                            limit_value=float(config.min_cash_buffer),
                        )
                    )

        if config is not None and config.daily_loss_limit_amount is not None:
            configured_limit_count += 1
        if config is not None and config.daily_loss_limit_pct is not None:
            configured_limit_count += 1

        return RiskLimitCheckResult(
            allowed=not violations,
            enforcement_enabled=False,
            trading_mode=trading_mode,
            evaluated_notional=float(evaluated_notional) if evaluated_notional is not None else None,
            configured_limit_count=configured_limit_count,
            violations=violations,
            note="Evaluation only. Risk limits are not enforced in broker submission during MH-38.",
        )

    @staticmethod
    def _to_model_data(payload: dict) -> dict:
        model_data = payload.copy()
        for field in _LIMIT_FIELDS:
            if field in model_data and model_data[field] is not None:
                value = model_data[field]
                if field in {"max_open_positions", "max_trades_per_day"}:
                    model_data[field] = int(value)
                else:
                    model_data[field] = Decimal(str(value))
        if "scope" in model_data and model_data["scope"] is not None:
            model_data["scope"] = str(model_data["scope"]).lower()
        if "trading_mode" in model_data and model_data["trading_mode"] is not None:
            model_data["trading_mode"] = str(model_data["trading_mode"]).lower()
        return model_data

    @staticmethod
    def _normalize_scalar(value):
        if isinstance(value, Decimal):
            return float(value)
        return value