"""Deterministic paper execution simulation service for MVP."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.models import AuditLog, PaperOrder, RiskDecision
from app.services.signal_service import SignalOutput

PaperExecutionStatus = Literal["submitted", "filled", "closed", "blocked"]
PaperSide = Literal["buy", "sell"]


# --------------------------------------------------------------------------- #
# Legacy stateless API (kept for backward compat with existing route handlers) #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PaperExecutionResult:
    """Typed result of stateless paper execution simulation."""

    execution_id: UUID
    status: PaperExecutionStatus
    asset: str
    timeframe: str
    side: PaperSide
    qty: float
    notional: float
    stop_price: float
    target_price: float
    fill_price: float
    reason: str | None = None


# --------------------------------------------------------------------------- #
# Session-based service (used by tests and new route handlers)                #
# --------------------------------------------------------------------------- #


class PaperExecutionService:
    """DB-backed paper order lifecycle service."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def create_order(
        self,
        risk_decision_id: UUID,
        asset_id: UUID,
        direction: str,
        quantity: float,
        limit_price: float | None = None,
    ) -> PaperOrder:
        """Create a pending paper order after validating risk decision approval.

        Raises:
            ValueError: If risk decision is not approved.
        """
        if self._session is None:
            raise RuntimeError("PaperExecutionService.create_order requires a database session")

        decision: RiskDecision | None = (
            self._session.query(RiskDecision)
            .filter(RiskDecision.id == risk_decision_id)
            .first()
        )
        if decision is None or not decision.approved:
            raise ValueError("risk decision is not approved")

        paper_side = "buy" if direction == "long" else "sell" if direction == "short" else direction
        order = PaperOrder(
            asset_id=asset_id,
            risk_decision_id=risk_decision_id,
            direction=paper_side,
            quantity=quantity,
            filled_quantity=0.0,
            limit_price=limit_price,
            status="pending",
            timestamp=datetime.now(UTC),
        )
        self._session.add(order)

        audit = AuditLog(
            entity_type="paper_order",
            entity_id=risk_decision_id,
            event_type="order_created",
            payload_json={"direction": paper_side, "quantity": quantity},
        )
        self._session.add(audit)
        self._session.commit()
        self._session.refresh(order)
        return order

    def simulate_fill(
        self,
        order_id: UUID,
        fill_price: float,
        fill_quantity: float | None = None,
    ) -> PaperOrder:
        """Simulate a fill event on a pending order."""
        if self._session is None:
            raise RuntimeError("PaperExecutionService.simulate_fill requires a database session")

        order: PaperOrder | None = (
            self._session.query(PaperOrder)
            .filter(PaperOrder.id == order_id)
            .first()
        )
        if order is None:
            raise ValueError(f"paper order {order_id} not found")

        qty = fill_quantity if fill_quantity is not None else float(order.quantity or 0)
        order.filled_quantity = float(order.filled_quantity or 0) + qty

        if order.filled_quantity >= float(order.quantity or 0):
            order.status = "filled"
        # else stays "pending" (partial fill)

        audit = AuditLog(
            entity_type="paper_order",
            entity_id=order_id,
            event_type="order_filled",
            payload_json={"fill_price": fill_price, "fill_quantity": qty},
        )
        self._session.add(audit)
        self._session.commit()
        return order

    def cancel_order(self, order_id: UUID, reason: str) -> PaperOrder:
        """Cancel a pending paper order."""
        if self._session is None:
            raise RuntimeError("PaperExecutionService.cancel_order requires a database session")

        order: PaperOrder | None = (
            self._session.query(PaperOrder)
            .filter(PaperOrder.id == order_id)
            .first()
        )
        if order is None:
            raise ValueError(f"paper order {order_id} not found")

        order.status = "canceled"
        self._session.commit()
        return order

    # ------------------------------------------------------------------ #
    # Legacy stateless helpers (kept for existing route handlers)         #
    # ------------------------------------------------------------------ #

    def submit_order(
        self,
        signal,
        allowed_risk_amount: float,
        latest_price: float,
    ) -> PaperExecutionResult:
        """Create a submitted paper execution result from approved signal inputs."""
        side = self._side_from_signal(signal.direction)
        entry_price = self._entry_price(signal, latest_price)

        qty = self._compute_qty(signal, side, entry_price, allowed_risk_amount)
        if qty <= 0.0:
            return self._blocked_result(signal, side, entry_price, reason="invalid_stop_distance")

        return PaperExecutionResult(
            execution_id=uuid4(),
            status="submitted",
            asset=signal.asset,
            timeframe=signal.timeframe,
            side=side,
            qty=qty,
            notional=qty * entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            fill_price=entry_price,
        )

    def fill_order(self, submitted: PaperExecutionResult) -> PaperExecutionResult:
        if submitted.status != "submitted":
            raise ValueError("Only submitted paper orders can be filled")
        return replace(submitted, status="filled")

    def close_order(self, filled: PaperExecutionResult, close_price: float) -> PaperExecutionResult:
        if filled.status != "filled":
            raise ValueError("Only filled paper orders can be closed")
        return replace(filled, status="closed", fill_price=close_price)

    def _entry_price(self, signal, latest_price: float) -> float:
        low, high = sorted(signal.entry_zone)
        if low <= latest_price <= high:
            return latest_price
        if latest_price < low:
            return low
        return high

    def _compute_qty(self, signal, side: PaperSide, fill_price: float, allowed_risk_amount: float) -> float:
        if allowed_risk_amount <= 0.0:
            return 0.0
        if side == "buy":
            stop_distance = fill_price - signal.stop_price
        else:
            stop_distance = signal.stop_price - fill_price
        if stop_distance <= 0.0:
            return 0.0
        return allowed_risk_amount / stop_distance

    def _side_from_signal(self, direction: str) -> PaperSide:
        if direction == "long":
            return "buy"
        if direction == "short":
            return "sell"
        raise ValueError("Paper execution requires long or short signal direction")

    def _blocked_result(self, signal, side: PaperSide, entry_price: float, reason: str) -> PaperExecutionResult:
        return PaperExecutionResult(
            execution_id=uuid4(),
            status="blocked",
            asset=signal.asset,
            timeframe=signal.timeframe,
            side=side,
            qty=0.0,
            notional=0.0,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            fill_price=entry_price,
            reason=reason,
        )


class StatelessPaperExecutionService:
    """Simulates paper order lifecycle without persistence or broker calls."""

    def submit_order(
        self,
        signal: SignalOutput,
        allowed_risk_amount: float,
        latest_price: float,
    ) -> PaperExecutionResult:
        """Create a submitted paper execution result from approved signal inputs."""
        side = self._side_from_signal(signal.direction)
        entry_price = self._entry_price(signal, latest_price)

        qty = self._compute_qty(signal, side, entry_price, allowed_risk_amount)
        if qty <= 0.0:
            return self._blocked_result(signal, side, entry_price, reason="invalid_stop_distance")

        return PaperExecutionResult(
            execution_id=uuid4(),
            status="submitted",
            asset=signal.asset,
            timeframe=signal.timeframe,
            side=side,
            qty=qty,
            notional=qty * entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            fill_price=entry_price,
        )

    def fill_order(self, submitted: PaperExecutionResult) -> PaperExecutionResult:
        """Transition a submitted result into filled status deterministically."""
        if submitted.status != "submitted":
            raise ValueError("Only submitted paper orders can be filled")
        return replace(submitted, status="filled")

    def close_order(self, filled: PaperExecutionResult, close_price: float) -> PaperExecutionResult:
        """Transition a filled result into closed status with provided close price."""
        if filled.status != "filled":
            raise ValueError("Only filled paper orders can be closed")
        return replace(filled, status="closed", fill_price=close_price)

    def _entry_price(self, signal: SignalOutput, latest_price: float) -> float:
        """Return latest price when inside zone, else nearest entry boundary."""
        low, high = sorted(signal.entry_zone)
        if low <= latest_price <= high:
            return latest_price
        if latest_price < low:
            return low
        return high

    def _compute_qty(
        self,
        signal: SignalOutput,
        side: PaperSide,
        fill_price: float,
        allowed_risk_amount: float,
    ) -> float:
        """Compute quantity from risk amount and stop distance, or 0 for invalid state."""
        if allowed_risk_amount <= 0.0:
            return 0.0

        if side == "buy":
            stop_distance = fill_price - signal.stop_price
        else:
            stop_distance = signal.stop_price - fill_price

        if stop_distance <= 0.0:
            return 0.0

        return allowed_risk_amount / stop_distance

    def _side_from_signal(self, direction: str) -> PaperSide:
        """Map signal direction to deterministic paper side."""
        if direction == "long":
            return "buy"
        if direction == "short":
            return "sell"
        raise ValueError("Paper execution requires long or short signal direction")

    def _blocked_result(
        self,
        signal: SignalOutput,
        side: PaperSide,
        entry_price: float,
        reason: str,
    ) -> PaperExecutionResult:
        """Build a blocked paper execution result with zero quantity."""
        return PaperExecutionResult(
            execution_id=uuid4(),
            status="blocked",
            asset=signal.asset,
            timeframe=signal.timeframe,
            side=side,
            qty=0.0,
            notional=0.0,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            fill_price=entry_price,
            reason=reason,
        )
