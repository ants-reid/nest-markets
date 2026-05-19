"""Service for drafting and managing paper trading recommendations."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import PaperRecommendation
from app.db.models.paper_recommendation import PaperRecommendationStatus

_logger = logging.getLogger(__name__)


class PaperRecommendationService:
    """Service for drafting and managing paper trading recommendations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def draft_recommendation(
        self,
        ticker: str,
        side: str,
        quantity: float,
        order_type: str,
        limit_price: float | None = None,
        signal_id: UUID | None = None,
        model_version_id: UUID | None = None,
        confidence: float | None = None,
        risk_score: float | None = None,
        rationale: str | None = None,
    ) -> PaperRecommendation:
        """Create a new paper trading recommendation draft.

        Args:
            ticker: Trade ticker (e.g., 'AAPL')
            side: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
            limit_price: Limit price for LIMIT orders
            signal_id: Optional reference to source signal
            model_version_id: Optional reference to source model
            confidence: Optional confidence metric (0.0-1.0)
            risk_score: Optional risk score (0.0-1.0, higher = riskier)
            rationale: Optional explanation for the recommendation

        Returns:
            Created PaperRecommendation record.
        """
        # Calculate estimated notional (simplified; uses limit_price or a placeholder)
        price = limit_price if limit_price else 100.0  # Default placeholder
        estimated_notional = quantity * price

        rec = PaperRecommendation(
            ticker=ticker,
            side=side,
            quantity=Decimal(str(quantity)),
            order_type=order_type,
            limit_price=Decimal(str(limit_price)) if limit_price else None,
            signal_id=signal_id,
            model_version_id=model_version_id,
            confidence=Decimal(str(confidence)) if confidence else None,
            risk_score=Decimal(str(risk_score)) if risk_score else None,
            estimated_notional=Decimal(str(estimated_notional)),
            rationale=rationale,
            status=PaperRecommendationStatus.DRAFT,
        )

        self._session.add(rec)
        self._session.commit()

        _logger.info(
            "Drafted paper recommendation: %s %s %s @ %s (id=%s)",
            side,
            quantity,
            ticker,
            order_type,
            rec.id,
        )

        return rec

    def get_recommendation(self, rec_id: UUID) -> PaperRecommendation | None:
        """Get a recommendation by ID."""
        return self._session.query(PaperRecommendation).filter(PaperRecommendation.id == rec_id).first()

    def list_recommendations(self, status: str | None = None, limit: int = 20) -> list[PaperRecommendation]:
        """List paper recommendations, optionally filtered by status.

        Args:
            status: Optional status filter (e.g., 'draft', 'approved', 'executed')
            limit: Maximum number of results (ordered by created_at DESC)

        Returns:
            List of PaperRecommendation records.
        """
        query = self._session.query(PaperRecommendation)

        if status:
            query = query.filter(PaperRecommendation.status == status)

        return query.order_by(desc(PaperRecommendation.created_at)).limit(limit).all()

    def review_recommendation(
        self, rec_id: UUID, approved: bool, reviewed_by: str | None = None, notes: str | None = None
    ) -> PaperRecommendation | None:
        """Review and decide on a recommendation draft.

        Args:
            rec_id: Recommendation ID
            approved: True to approve, False to reject
            reviewed_by: Username or operator ID who reviewed
            notes: Optional review notes

        Returns:
            Updated PaperRecommendation, or None if not found.
        """
        rec = self.get_recommendation(rec_id)
        if not rec:
            return None

        if rec.status != PaperRecommendationStatus.DRAFT:
            _logger.warning("Cannot review recommendation %s; already in status %s", rec_id, rec.status)
            return rec

        rec.status = PaperRecommendationStatus.APPROVED if approved else PaperRecommendationStatus.REJECTED
        rec.reviewed_at = datetime.now(timezone.utc)
        rec.reviewed_by = reviewed_by
        rec.review_notes = notes

        self._session.commit()

        _logger.info(
            "Reviewed paper recommendation %s: %s (by %s)",
            rec_id,
            "APPROVED" if approved else "REJECTED",
            reviewed_by or "unknown",
        )

        return rec

    def mark_executed(self, rec_id: UUID, paper_order_ids: list[str] | None = None) -> PaperRecommendation | None:
        """Mark a recommendation as executed.

        Args:
            rec_id: Recommendation ID
            paper_order_ids: List of broker order IDs that were submitted

        Returns:
            Updated PaperRecommendation, or None if not found.
        """
        rec = self.get_recommendation(rec_id)
        if not rec:
            return None

        if rec.status not in {PaperRecommendationStatus.APPROVED, PaperRecommendationStatus.DRAFT}:
            _logger.warning(
                "Cannot execute recommendation %s; status is %s (not approved or draft)", rec_id, rec.status
            )
            return rec

        rec.status = PaperRecommendationStatus.EXECUTED
        rec.executed_at = datetime.now(timezone.utc)
        rec.paper_order_ids = paper_order_ids or []

        self._session.commit()

        _logger.info("Marked paper recommendation %s as executed (orders: %s)", rec_id, paper_order_ids)

        return rec
