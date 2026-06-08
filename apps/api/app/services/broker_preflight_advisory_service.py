"""Broker preflight advisory helper service.

Collects dry-run advisory warnings and context from trading-halt and risk-limit
services. This module is read/evaluation-only and never submits orders.
"""

from __future__ import annotations

from typing import Any

from app.clients.broker.broker_interface import OrderRequest
from app.db.session import SessionLocal, ensure_public_search_path
from app.services.broker_mode_guard import get_broker_mode_metadata
from app.services.risk_limit_service import RiskLimitService
from app.services.trading_halt_service import TradingHaltService


class BrokerPreflightAdvisoryService:
    """Build advisory warnings and context for broker dry-run responses."""

    def collect_preflight_warnings(
        self,
        request: OrderRequest,
        estimated_notional: float | None,
        portfolio_context: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        preflight_data: dict[str, Any] = {}
        session = SessionLocal()
        ensure_public_search_path(session)

        try:
            trading_mode = str(get_broker_mode_metadata().get("mode") or "paper").lower()

            halt_status = TradingHaltService(session).get_status(scope="global")
            if halt_status.emergency_stop_active:
                warnings.append(
                    {
                        "code": "emergency_stop_active",
                        "message": halt_status.blocked_reason
                        or "Trading halt is active and will be enforced in a later execution phase.",
                        "severity": "warning",
                        "source": "trading_halt",
                        "enforcement_enabled": True,
                    }
                )

            risk_service = RiskLimitService(session)
            risk_status = risk_service.get_status(trading_mode=trading_mode)

            active_config = risk_status.active_config
            if active_config is not None:
                preflight_data["risk_limit_snapshot"] = {
                    "scope": active_config.scope,
                    "trading_mode": active_config.trading_mode,
                    "max_order_notional": active_config.max_order_notional,
                    "daily_loss_limit_amount": active_config.daily_loss_limit_amount,
                    "daily_loss_limit_pct": active_config.daily_loss_limit_pct,
                    "max_open_positions": active_config.max_open_positions,
                    "max_total_exposure": active_config.max_total_exposure,
                    "max_symbol_exposure": active_config.max_symbol_exposure,
                    "max_trades_per_day": active_config.max_trades_per_day,
                    "min_cash_buffer": active_config.min_cash_buffer,
                }

            if portfolio_context:
                for key in (
                    "cash_balance",
                    "buying_power",
                    "open_position_count",
                    "current_symbol_exposure",
                    "current_total_exposure",
                    "daily_pnl",
                    "daily_loss",
                ):
                    if portfolio_context.get(key) is not None:
                        preflight_data[key] = portfolio_context[key]

                if estimated_notional is not None and request.side == "BUY":
                    sym_exp = portfolio_context.get("current_symbol_exposure")
                    if sym_exp is not None:
                        preflight_data["estimated_post_trade_symbol_exposure"] = (
                            float(sym_exp) + estimated_notional
                        )
                    tot_exp = portfolio_context.get("current_total_exposure")
                    if tot_exp is not None:
                        preflight_data["estimated_post_trade_total_exposure"] = (
                            float(tot_exp) + estimated_notional
                        )

            if risk_status.has_max_order_notional:
                warnings.append(
                    {
                        "code": "max_order_notional_configured",
                        "message": "Max order notional is configured for future enforcement and is evaluated here as advisory only.",
                        "severity": "warning",
                        "source": "risk_limits",
                        "enforcement_enabled": False,
                    }
                )
            else:
                warnings.append(
                    {
                        "code": "max_order_notional_not_configured",
                        "message": "Max order notional is not configured; future preflight enforcement remains pending.",
                        "severity": "warning",
                        "source": "risk_limits",
                        "enforcement_enabled": False,
                    }
                )

            if estimated_notional is not None:
                order_eval_context: dict[str, Any] = {
                    "ticker": request.ticker,
                    "side": request.side,
                    "quantity": float(request.quantity),
                    "estimated_notional": estimated_notional,
                    "trading_mode": trading_mode,
                }
                if portfolio_context:
                    if portfolio_context.get("current_total_exposure") is not None:
                        order_eval_context["current_total_exposure"] = portfolio_context["current_total_exposure"]
                    if portfolio_context.get("current_symbol_exposure") is not None:
                        order_eval_context["current_symbol_exposure"] = portfolio_context["current_symbol_exposure"]
                    if portfolio_context.get("open_position_count") is not None:
                        order_eval_context["current_open_positions"] = portfolio_context["open_position_count"]
                    if portfolio_context.get("cash_balance") is not None:
                        order_eval_context["available_cash"] = portfolio_context["cash_balance"]

                evaluation = risk_service.evaluate_order_against_limits(order_eval_context)
                for violation in evaluation.violations:
                    warnings.append(
                        {
                            "code": violation.code,
                            "message": violation.message,
                            "severity": "warning",
                            "source": "risk_limits",
                            "enforcement_enabled": False,
                        }
                    )
            elif risk_status.has_max_order_notional:
                warnings.append(
                    {
                        "code": "max_order_notional_not_evaluated",
                        "message": "Estimated notional could not be evaluated for this dry-run payload.",
                        "severity": "warning",
                        "source": "risk_limits",
                        "enforcement_enabled": False,
                    }
                )

            if risk_status.has_daily_loss_limit:
                warnings.append(
                    {
                        "code": "daily_loss_limit_placeholder",
                        "message": "Daily loss limits are configured for future enforcement, but current dry-run does not yet calculate intraday realized loss context.",
                        "severity": "warning",
                        "source": "risk_limits",
                        "enforcement_enabled": False,
                    }
                )
            else:
                warnings.append(
                    {
                        "code": "daily_loss_limit_not_configured",
                        "message": "Daily loss limits are not configured; future enforcement remains pending.",
                        "severity": "warning",
                        "source": "risk_limits",
                        "enforcement_enabled": False,
                    }
                )

            has_exposure_limit = risk_status.has_max_total_exposure or (
                "max_symbol_exposure" in risk_status.configured_limits
            )
            has_exposure_context = portfolio_context is not None and (
                portfolio_context.get("current_total_exposure") is not None
                or portfolio_context.get("current_symbol_exposure") is not None
            )
            if has_exposure_limit and not has_exposure_context:
                warnings.append(
                    {
                        "code": "max_exposure_placeholder",
                        "message": "Exposure limits are configured for future enforcement, but current dry-run does not yet include live portfolio exposure context.",
                        "severity": "warning",
                        "source": "risk_limits",
                        "enforcement_enabled": False,
                    }
                )
            elif not has_exposure_limit:
                warnings.append(
                    {
                        "code": "max_exposure_not_configured",
                        "message": "Exposure limits are not configured; future enforcement remains pending.",
                        "severity": "warning",
                        "source": "risk_limits",
                        "enforcement_enabled": False,
                    }
                )
        finally:
            session.close()

        return warnings, preflight_data