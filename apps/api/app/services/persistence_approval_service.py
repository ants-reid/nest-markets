"""Persistence mapper for approval workflow outputs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import ApprovalStatus
from app.db.models.asset import Asset
from app.db.models.approval_request import ApprovalRequest as ApprovalRequestModel
from app.db.models.risk_decision import RiskDecision as RiskDecisionModel
from app.db.models.signal import Signal as SignalModel
from app.services.approval_service import ApprovalRequest
from app.services.signal_service import SignalOutput


class PersistenceApprovalService:
    """Persist typed approval workflow state into ORM approval request rows."""

    def __init__(self, session: Session) -> None:
        """Initialize service with an explicit SQLAlchemy session."""
        self._session = session

    def persist_approval_request(
        self,
        signal_id: UUID,
        approval_request: ApprovalRequest,
    ) -> ApprovalRequestModel:
        """Create or update a persisted approval request row."""
        row = self._session.get(ApprovalRequestModel, approval_request.request_id)

        if row is None:
            row = ApprovalRequestModel(id=approval_request.request_id, signal_id=signal_id)
            self._session.add(row)

        row.signal_id = signal_id
        row.status = ApprovalStatus(approval_request.status)
        row.requested_at = approval_request.created_at
        row.expires_at = approval_request.expires_at
        if approval_request.status != "pending" and row.responded_at is None:
            row.responded_at = datetime.now(UTC)

        self._session.flush()
        self._session.refresh(row)
        return row

    def get_approval_request(self, request_id: UUID) -> ApprovalRequestModel | None:
        """Return one persisted approval request row by id."""
        return self._session.get(ApprovalRequestModel, request_id)

    def build_service_request(self, row: ApprovalRequestModel) -> ApprovalRequest:
        """Hydrate a typed approval request from persisted approval and signal rows."""
        signal = self._session.get(SignalModel, row.signal_id)
        if signal is None:
            raise ValueError(f"Signal '{row.signal_id}' not found for approval request '{row.id}'")

        asset = self._session.get(Asset, signal.asset_id)
        if asset is None:
            raise ValueError(f"Asset '{signal.asset_id}' not found for approval request '{row.id}'")

        created_at = row.requested_at or row.created_at
        expires_at = row.expires_at or created_at

        return ApprovalRequest(
            request_id=row.id,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            created_at=created_at,
            expires_at=expires_at,
            asset=asset.symbol,
            timeframe=signal.timeframe,
            execution_mode="confirm_live",
        )

    def build_paper_execution_inputs(
        self,
        row: ApprovalRequestModel,
    ) -> tuple[SignalOutput, float, float]:
        """Hydrate signal and execution sizing inputs for post-approval paper execution."""
        signal = self._session.get(SignalModel, row.signal_id)
        if signal is None:
            raise ValueError(f"Signal '{row.signal_id}' not found for approval request '{row.id}'")

        asset = self._session.get(Asset, signal.asset_id)
        if asset is None:
            raise ValueError(f"Asset '{signal.asset_id}' not found for approval request '{row.id}'")

        risk_decision = self._session.execute(
            select(RiskDecisionModel).where(RiskDecisionModel.signal_id == row.signal_id)
        ).scalar_one_or_none()

        allowed_risk_amount = 0.0
        if risk_decision is not None and risk_decision.notional_allowed is not None:
            allowed_risk_amount = float(risk_decision.notional_allowed)

        entry_min = float(signal.entry_min or 0.0)
        entry_max = float(signal.entry_max or entry_min)
        latest_price = (entry_min + entry_max) / 2.0

        signal_output = SignalOutput(
            asset=asset.symbol,
            timeframe=signal.timeframe,
            direction=signal.direction.value,
            regime=signal.regime.value if signal.regime is not None else "range",
            setup_type=signal.setup_type.value,
            entry_zone=(entry_min, entry_max),
            stop_price=float(signal.stop_price or 0.0),
            target_price=float(signal.target_price or 0.0),
            confidence=float(signal.confidence or 0.0),
            horizon_label=signal.horizon_label.value if signal.horizon_label is not None else "intraday",
            catalyst_type=signal.catalyst_type.value if signal.catalyst_type is not None else "none",
            catalyst_score=float(signal.catalyst_score or 0.0),
            catalyst_summary=signal.catalyst_summary or "",
            thesis=signal.thesis or "",
            invalidators=[str(item) for item in (signal.invalidators_json or [])],
            signal_score=float(signal.signal_score or 0.0),
            should_trade=signal.direction.value != "flat",
        )

        return signal_output, allowed_risk_amount, latest_price
