"""Persistence mapper for deterministic paper execution results."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.enums import OrderStatus
from app.db.models.asset import Asset
from app.db.models.mixins import utc_now
from app.db.models.paper_order import PaperOrder
from app.db.models.signal import Signal as SignalModel
from app.services.paper_execution_service import PaperExecutionResult
from app.services.visual_seed import VISUAL_SEED_PROVIDER


class PersistencePaperExecutionService:
    """Persist paper execution lifecycle outputs into paper order rows."""

    def __init__(self, session: Session) -> None:
        """Initialize service with an explicit SQLAlchemy session."""
        self._session = session

    def persist_paper_execution(
        self,
        signal_id: UUID,
        result: PaperExecutionResult,
        *,
        order_type: str = "market",
        submitted_at: datetime | None = None,
    ) -> PaperOrder:
        """Create or update a paper order row from a typed execution result."""
        order = self._session.get(PaperOrder, result.execution_id)

        if order is None:
            order = PaperOrder(id=result.execution_id, signal_id=signal_id, order_type=order_type)
            self._session.add(order)

        order.signal_id = signal_id
        order.order_type = order_type
        order.side = result.side
        order.qty = result.qty
        order.notional = result.notional
        order.limit_price = None
        order.stop_price = result.stop_price
        order.status = self._map_status(result.status)
        order.submitted_at = submitted_at or order.submitted_at or utc_now()

        self._session.flush()
        self._session.refresh(order)
        return order

    def get_paper_order(self, execution_id: UUID) -> PaperOrder | None:
        """Return one persisted paper order row by execution id."""
        return self._session.get(PaperOrder, execution_id)

    def list_paper_orders(
        self,
        *,
        limit: int,
        offset: int,
        status: OrderStatus | None = None,
        include_visual_seed: bool = False,
    ) -> list[PaperOrder]:
        """Return paper orders in deterministic order with simple pagination."""
        statement = select(PaperOrder)
        if status is not None:
            statement = statement.where(PaperOrder.status == status)

        if not include_visual_seed:
            statement = (
                statement
                .outerjoin(SignalModel, PaperOrder.signal_id == SignalModel.id)
                .where(
                    or_(
                        PaperOrder.signal_id.is_(None),
                        SignalModel.provider_name.is_(None),
                        SignalModel.provider_name != VISUAL_SEED_PROVIDER,
                    )
                )
            )

        statement = statement.order_by(PaperOrder.created_at.asc(), PaperOrder.id.asc())
        statement = statement.offset(offset).limit(limit)
        return list(self._session.execute(statement).scalars().all())

    def build_service_result(self, order: PaperOrder) -> PaperExecutionResult:
        """Hydrate a typed paper execution result from a persisted paper order row."""
        signal = self._session.get(SignalModel, order.signal_id)
        if signal is None:
            raise ValueError(f"Signal '{order.signal_id}' not found for paper order '{order.id}'")

        asset = self._session.get(Asset, signal.asset_id)
        if asset is None:
            raise ValueError(f"Asset '{signal.asset_id}' not found for paper order '{order.id}'")

        qty = float(order.qty or 0.0)
        notional = float(order.notional or 0.0)
        fill_price = (notional / qty) if qty > 0.0 else 0.0

        return PaperExecutionResult(
            execution_id=order.id,
            status=self._to_service_status(order.status),
            asset=asset.symbol,
            timeframe=signal.timeframe,
            side=order.side,
            qty=qty,
            notional=notional,
            stop_price=float(order.stop_price or 0.0),
            target_price=float(signal.target_price or 0.0),
            fill_price=fill_price,
            reason=None,
        )

    def build_history_events(self, order: PaperOrder) -> list[str]:
        """Return chronological lifecycle event names for one persisted paper order."""
        status = self._to_service_status(order.status)
        if status == "submitted":
            return ["submitted"]
        if status == "filled":
            return ["submitted", "filled"]
        if status == "closed":
            return ["submitted", "filled", "closed"]
        return ["submitted"]

    def _map_status(self, value: str) -> OrderStatus:
        """Map domain paper execution status to ORM order status."""
        if value == "submitted":
            return OrderStatus.ACCEPTED
        if value == "filled":
            return OrderStatus.FILLED
        if value == "closed":
            return OrderStatus.CLOSED
        if value == "blocked":
            return OrderStatus.REJECTED
        raise ValueError(f"Unsupported paper execution status '{value}'")

    def _to_service_status(self, value: "OrderStatus | str") -> str:
        """Map ORM order status back to domain paper execution status.

        The status column is a plain String(50); the DB may store values in any
        case (e.g. 'CLOSED', 'ACCEPTED').  Normalise to the canonical lowercase
        enum before comparing so case mismatches don't raise.
        """
        if isinstance(value, str) and not isinstance(value, OrderStatus):
            try:
                value = OrderStatus(value.lower())
            except ValueError:
                raise ValueError(f"Unsupported order status '{value}'")
        if value in (OrderStatus.PENDING, OrderStatus.NEW, OrderStatus.ACCEPTED):
            return "submitted"
        if value == OrderStatus.FILLED:
            return "filled"
        if value == OrderStatus.CLOSED:
            return "closed"
        if value in (OrderStatus.CANCELED, OrderStatus.REJECTED):
            return "blocked"
        raise ValueError(f"Unsupported order status '{value}'")
