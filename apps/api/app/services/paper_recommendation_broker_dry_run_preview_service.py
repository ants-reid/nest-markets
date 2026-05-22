"""Guarded broker dry-run preview service for persisted recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.clients.broker.broker_interface import OrderRequest
from app.services.broker_service import BrokerService
from app.services.paper_recommendation_route_check_service import (
    PaperRecommendationRouteCheckDecision,
    PaperRecommendationRouteCheckService,
)
from app.services.paper_source_contract import broker_dry_run_sources


@dataclass(frozen=True)
class PaperRecommendationBrokerDryRunPreviewDecision:
    recommendation_id: UUID
    recommendation_status: str
    ticker: str | None
    side: str | None
    quantity: float | None
    order_type: str | None
    limit_price: float | None
    estimated_notional: float | None
    risk_score: float | None
    route_check_status: str
    dry_run_status: str
    dry_run_only: bool
    dry_run_executed: bool
    allowed_to_submit: bool | None
    resolved_route: str | None
    resolved_execution_source: str | None
    dry_run_execution_source: str | None
    balance_source: str | None
    fees_source: str | None
    fills_source: str | None
    positions_source: str | None
    serious_paper_source: str
    is_canonical_paper: bool
    broker_account_mode: str
    live_state: str
    would_block: bool
    blocked_reason: str | None
    missing_data: list[str]
    next_required_action: str
    is_submit: bool
    workers_allowed_to_submit: bool
    live_trading_enabled: bool
    canonical_paper_route: str
    broker_mode: dict[str, object]
    mode_guard_ok: bool | None
    request_valid: bool | None
    issues: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    preflight_decision: dict[str, Any] | None
    preflight_context: dict[str, Any] | None
    paper_path_note: str | None


class PaperRecommendationBrokerDryRunPreviewService:
    """Run the existing broker dry-run only after route-check eligibility."""

    def __init__(self, session: Session) -> None:
        self._route_checks = PaperRecommendationRouteCheckService(session)

    def resolve_preview(
        self, recommendation_id: UUID
    ) -> PaperRecommendationBrokerDryRunPreviewDecision | None:
        route_check = self._route_checks.resolve_route_check(recommendation_id)
        if route_check is None:
            return None

        if route_check.route_check_status != "eligible":
            dry_run_status = "missing_context" if route_check.route_check_status == "missing_context" else "blocked"
            return PaperRecommendationBrokerDryRunPreviewDecision(
                recommendation_id=route_check.recommendation_id,
                recommendation_status=route_check.recommendation_status,
                ticker=route_check.ticker,
                side=route_check.side,
                quantity=route_check.quantity,
                order_type=route_check.order_type,
                limit_price=route_check.limit_price,
                estimated_notional=route_check.estimated_notional,
                risk_score=route_check.risk_score,
                route_check_status=route_check.route_check_status,
                dry_run_status=dry_run_status,
                dry_run_only=True,
                dry_run_executed=False,
                allowed_to_submit=False,
                resolved_route=route_check.resolved_route,
                resolved_execution_source=route_check.resolved_execution_source,
                dry_run_execution_source=None,
                balance_source=None,
                fees_source=None,
                fills_source=None,
                positions_source=None,
                serious_paper_source=route_check.serious_paper_source,
                is_canonical_paper=route_check.is_canonical_paper,
                broker_account_mode=route_check.broker_account_mode,
                live_state=route_check.live_state,
                would_block=True,
                blocked_reason=route_check.blocked_reason,
                missing_data=list(route_check.missing_data),
                next_required_action=route_check.next_required_action,
                is_submit=False,
                workers_allowed_to_submit=route_check.workers_allowed_to_submit,
                live_trading_enabled=route_check.live_trading_enabled,
                canonical_paper_route=route_check.canonical_paper_route,
                broker_mode=dict(route_check.broker_mode),
                mode_guard_ok=None,
                request_valid=None,
                issues=[],
                warnings=[],
                preflight_decision=None,
                preflight_context=None,
                paper_path_note=(
                    "Guarded broker dry-run preview was not executed because the "
                    "recommendation did not pass the serious-paper route-check."
                ),
            )

        dry_run_result = BrokerService().dry_run_order(
            self._build_order_request(route_check),
            portfolio_context=None,
            persist_decision=True,
            decision_source="dry_run",
            intent="manual",
        )
        broker_mode = dict(dry_run_result.get("broker_mode") or route_check.broker_mode)
        source_labels = broker_dry_run_sources(broker_mode)
        preflight_decision = dict(dry_run_result.get("preflight_decision") or {})
        decision_status = str(preflight_decision.get("decision_status") or "unknown").lower()
        allowed_to_submit = (
            dry_run_result.get("status") == "ready"
            and bool(dry_run_result.get("mode_guard_ok"))
            and bool(dry_run_result.get("request_valid"))
            and decision_status in {"allowed", "advisory"}
        )

        return PaperRecommendationBrokerDryRunPreviewDecision(
            recommendation_id=route_check.recommendation_id,
            recommendation_status=route_check.recommendation_status,
            ticker=route_check.ticker,
            side=route_check.side,
            quantity=route_check.quantity,
            order_type=route_check.order_type,
            limit_price=route_check.limit_price,
            estimated_notional=dry_run_result.get("estimated_notional"),
            risk_score=route_check.risk_score,
            route_check_status=route_check.route_check_status,
            dry_run_status=str(dry_run_result.get("status") or "blocked"),
            dry_run_only=True,
            dry_run_executed=True,
            allowed_to_submit=allowed_to_submit,
            resolved_route=route_check.resolved_route,
            resolved_execution_source=route_check.resolved_execution_source,
            dry_run_execution_source=str(source_labels.get("execution_source") or "broker_dry_run"),
            balance_source=str(source_labels.get("balance_source") or "ibkr_paper"),
            fees_source=str(source_labels.get("fees_source") or "pending_broker_report"),
            fills_source=str(source_labels.get("fills_source") or "pending_broker_fill"),
            positions_source=str(source_labels.get("positions_source") or "ibkr_paper"),
            serious_paper_source=str(source_labels.get("serious_paper_source") or route_check.serious_paper_source),
            is_canonical_paper=bool(source_labels.get("is_canonical_paper")),
            broker_account_mode=str(source_labels.get("broker_account_mode") or route_check.broker_account_mode),
            live_state=str(source_labels.get("live_state") or route_check.live_state),
            would_block=not allowed_to_submit,
            blocked_reason=self._dry_run_blocked_reason(route_check, dry_run_result),
            missing_data=list(route_check.missing_data),
            next_required_action=self._dry_run_next_required_action(route_check, dry_run_result, allowed_to_submit),
            is_submit=False,
            workers_allowed_to_submit=route_check.workers_allowed_to_submit,
            live_trading_enabled=route_check.live_trading_enabled,
            canonical_paper_route=str(source_labels.get("canonical_paper_route") or route_check.canonical_paper_route),
            broker_mode=broker_mode,
            mode_guard_ok=bool(dry_run_result.get("mode_guard_ok")),
            request_valid=bool(dry_run_result.get("request_valid")),
            issues=list(dry_run_result.get("issues") or []),
            warnings=list(dry_run_result.get("warnings") or []),
            preflight_decision=preflight_decision,
            preflight_context=dry_run_result.get("preflight_context"),
            paper_path_note=(
                dry_run_result.get("paper_path_note")
                or "Dry-run validates the IBKR paper submit path without placing an order."
            ),
        )

    @staticmethod
    def _build_order_request(route_check: PaperRecommendationRouteCheckDecision) -> OrderRequest:
        return OrderRequest(
            ticker=route_check.ticker or "",
            side=route_check.side or "",
            quantity=Decimal(str(route_check.quantity or 0)),
            order_type=route_check.order_type or "",
            limit_price=(Decimal(str(route_check.limit_price)) if route_check.limit_price is not None else None),
        )

    @staticmethod
    def _dry_run_blocked_reason(
        route_check: PaperRecommendationRouteCheckDecision,
        dry_run_result: dict[str, Any],
    ) -> str | None:
        if dry_run_result.get("status") == "blocked":
            issues = list(dry_run_result.get("issues") or [])
            if issues:
                return str(issues[0].get("message") or route_check.blocked_reason or "Dry-run is blocked.")

        preflight_decision = dict(dry_run_result.get("preflight_decision") or {})
        if str(preflight_decision.get("decision_status") or "").lower() in {"would_block", "blocked"}:
            for key in ("blocking_items", "would_block_items"):
                items = list(preflight_decision.get(key) or [])
                if items:
                    return str(items[0].get("message") or "Dry-run surfaced a blocking preflight finding.")

        return route_check.blocked_reason

    @staticmethod
    def _dry_run_next_required_action(
        route_check: PaperRecommendationRouteCheckDecision,
        dry_run_result: dict[str, Any],
        allowed_to_submit: bool,
    ) -> str:
        if allowed_to_submit:
            return (
                "Review this guarded broker dry-run preview, then use the existing POST /broker/orders "
                "manual paper submit path only if the operator still accepts the preflight findings."
            )

        if dry_run_result.get("status") == "invalid":
            return "Correct the recommendation order fields before using the guarded manual IBKR paper submit path."

        preflight_decision = dict(dry_run_result.get("preflight_decision") or {})
        if str(preflight_decision.get("decision_status") or "").lower() in {"would_block", "blocked"}:
            return (
                "Resolve the dry-run preflight findings before considering the existing POST /broker/orders "
                "manual paper submit path."
            )

        return route_check.next_required_action