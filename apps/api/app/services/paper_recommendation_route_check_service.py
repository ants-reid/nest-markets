"""Read-only route-check service for operator-driven serious-paper recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import PaperRecommendation
from app.db.models.paper_recommendation import PaperRecommendationStatus
from app.services.paper_recommendation_service import PaperRecommendationService
from app.services.serious_paper_routing_service import SeriousPaperRoutingService
from app.services.trading_control_service import get_trading_mode


@dataclass(frozen=True)
class PaperRecommendationRouteCheckDecision:
    """Resolved non-submitting route-check for a persisted recommendation."""

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
    resolved_route: str | None
    resolved_execution_source: str | None
    execution_source: str
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


class PaperRecommendationRouteCheckService:
    """Resolve whether a recommendation can proceed toward manual IBKR paper submit."""

    def __init__(self, session: Session) -> None:
        self._recommendations = PaperRecommendationService(session)
        self._routing = SeriousPaperRoutingService()

    def resolve_route_check(
        self, recommendation_id: UUID
    ) -> PaperRecommendationRouteCheckDecision | None:
        """Return a read-only route decision for one recommendation."""
        recommendation = self._recommendations.get_recommendation(recommendation_id)
        if recommendation is None:
            return None

        routing = self._routing.resolve_route()
        trading_mode = get_trading_mode()
        missing_data = self._collect_missing_data(recommendation)
        status_block_reason = self._status_block_reason(recommendation)

        if status_block_reason is not None:
            route_check_status = "blocked"
            blocked_reason = status_block_reason
            next_required_action = (
                "Use a different approved recommendation before attempting the guarded manual "
                "IBKR paper submit path."
            )
        elif routing.would_block:
            route_check_status = "blocked"
            blocked_reason = routing.blocked_reason
            next_required_action = routing.next_required_action
        elif missing_data:
            route_check_status = "missing_context"
            blocked_reason = None
            next_required_action = (
                "Complete the missing recommendation context and operator approval before "
                "attempting manual IBKR paper submit."
            )
        else:
            route_check_status = "eligible"
            blocked_reason = None
            next_required_action = routing.next_required_action

        eligible = route_check_status == "eligible"

        return PaperRecommendationRouteCheckDecision(
            recommendation_id=recommendation.id,
            recommendation_status=str(recommendation.status),
            ticker=recommendation.ticker,
            side=recommendation.side,
            quantity=self._to_float(recommendation.quantity),
            order_type=recommendation.order_type,
            limit_price=self._to_float(recommendation.limit_price),
            estimated_notional=self._to_float(recommendation.estimated_notional),
            risk_score=self._to_float(recommendation.risk_score),
            route_check_status=route_check_status,
            resolved_route=routing.resolved_route if eligible else None,
            resolved_execution_source=routing.resolved_execution_source if eligible else None,
            execution_source="recommendation_route_check",
            serious_paper_source=routing.serious_paper_source,
            is_canonical_paper=eligible,
            broker_account_mode=routing.current_broker_account_mode,
            live_state=routing.live_state,
            would_block=not eligible,
            blocked_reason=blocked_reason,
            missing_data=missing_data,
            next_required_action=next_required_action,
            is_submit=False,
            workers_allowed_to_submit=trading_mode.auto_trading_allowed,
            live_trading_enabled=trading_mode.live_order_submission_allowed,
            canonical_paper_route=routing.canonical_paper_route,
            broker_mode=routing.broker_mode,
        )

    def _collect_missing_data(self, recommendation: PaperRecommendation) -> list[str]:
        missing: list[str] = []

        if not recommendation.ticker:
            missing.append("ticker is required")
        if not recommendation.side:
            missing.append("side is required")

        quantity = self._to_float(recommendation.quantity)
        if quantity is None or quantity <= 0:
            missing.append("quantity must be greater than zero")

        order_type = str(recommendation.order_type or "").upper()
        if not order_type:
            missing.append("order_type is required")
        if order_type in {"LIMIT", "STOP_LIMIT"} and recommendation.limit_price is None:
            missing.append("limit_price is required for LIMIT and STOP_LIMIT recommendations")
        if order_type in {"STOP", "STOP_LIMIT"}:
            missing.append(
                "stop_price is required for STOP and STOP_LIMIT recommendations, but this recommendation does not persist stop_price"
            )

        if str(recommendation.status) != PaperRecommendationStatus.APPROVED:
            missing.append("operator approval is required before manual IBKR paper submit")

        return missing

    @staticmethod
    def _status_block_reason(recommendation: PaperRecommendation) -> str | None:
        status = str(recommendation.status)
        if status == PaperRecommendationStatus.REJECTED:
            return "Recommendation is rejected and is not eligible for manual IBKR paper submit."
        if status == PaperRecommendationStatus.EXECUTED:
            return "Recommendation is already executed and cannot be routed again."
        return None

    @staticmethod
    def _to_float(value: Decimal | float | None) -> float | None:
        if value is None:
            return None
        return float(value)