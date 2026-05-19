"""Position service — open, update, and close paper positions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.enums import PositionStatus
from app.db.models.position import Position


@dataclass
class OpenPositionInput:
    """Typed input for opening a new position."""

    asset_id: UUID
    signal_id: UUID | None
    side: str  # "long" | "short"
    avg_entry_price: float
    qty: float
    stop_price: float | None = None
    target_price: float | None = None


@dataclass
class PositionResult:
    """Typed result returned from position service operations."""

    id: UUID
    asset_id: UUID
    signal_id: UUID | None
    status: str
    side: str
    avg_entry_price: float | None
    current_price: float | None
    stop_price: float | None
    target_price: float | None
    qty: float | None
    opened_at: datetime | None
    closed_at: datetime | None
    close_reason: str | None
    realized_pnl: float | None
    unrealized_pnl: float | None


class PositionService:
    """Manage the lifecycle of paper positions.

    Responsibilities:
      - Open a new position from a filled paper order.
      - Mark a position to market (update current_price / unrealized_pnl).
      - Close a position and record realized_pnl.
      - List open positions.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_position(self, inp: OpenPositionInput) -> PositionResult:
        """Create a new OPEN position row."""
        row = Position(
            asset_id=inp.asset_id,
            signal_id=inp.signal_id,
            status=PositionStatus.OPEN,
            side=inp.side,
            avg_entry_price=inp.avg_entry_price,
            qty=inp.qty,
            stop_price=inp.stop_price,
            target_price=inp.target_price,
            opened_at=datetime.now(UTC),
            unrealized_pnl=0.0,
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return self._to_result(row)

    def mark_to_market(self, position_id: UUID, current_price: float) -> PositionResult:
        """Update current_price and recalculate unrealized_pnl."""
        row = self._get_open_or_raise(position_id)
        row.current_price = current_price
        row.unrealized_pnl = self._calc_unrealized(row, current_price)
        self._session.flush()
        self._session.refresh(row)
        return self._to_result(row)

    def close_position(
        self,
        position_id: UUID,
        *,
        close_price: float,
        close_reason: str = "manual",
    ) -> PositionResult:
        """Close a position and record realized_pnl."""
        row = self._get_open_or_raise(position_id)
        row.status = PositionStatus.CLOSED
        row.current_price = close_price
        row.closed_at = datetime.now(UTC)
        row.close_reason = close_reason
        row.realized_pnl = self._calc_unrealized(row, close_price)
        row.unrealized_pnl = 0.0
        self._session.flush()
        self._session.refresh(row)
        return self._to_result(row)

    def list_open_positions(self) -> list[PositionResult]:
        """Return all currently open positions."""
        rows = (
            self._session.query(Position)
            .filter(Position.status == PositionStatus.OPEN)
            .all()
        )
        return [self._to_result(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_open_or_raise(self, position_id: UUID) -> Position:
        row = self._session.get(Position, position_id)
        if row is None:
            raise ValueError(f"Position '{position_id}' not found")
        if row.status != PositionStatus.OPEN:
            raise ValueError(f"Position '{position_id}' is not open (status={row.status})")
        return row

    @staticmethod
    def _calc_unrealized(row: Position, current_price: float) -> float:
        qty = float(row.qty or 0)
        entry = float(row.avg_entry_price or 0)
        if qty == 0 or entry == 0:
            return 0.0
        if row.side == "long":
            return (current_price - entry) * qty
        return (entry - current_price) * qty

    @staticmethod
    def _to_result(row: Position) -> PositionResult:
        return PositionResult(
            id=row.id,
            asset_id=row.asset_id,
            signal_id=row.signal_id,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            side=row.side,
            avg_entry_price=float(row.avg_entry_price) if row.avg_entry_price is not None else None,
            current_price=float(row.current_price) if row.current_price is not None else None,
            stop_price=float(row.stop_price) if row.stop_price is not None else None,
            target_price=float(row.target_price) if row.target_price is not None else None,
            qty=float(row.qty) if row.qty is not None else None,
            opened_at=row.opened_at,
            closed_at=row.closed_at,
            close_reason=row.close_reason,
            realized_pnl=float(row.realized_pnl) if row.realized_pnl is not None else None,
            unrealized_pnl=float(row.unrealized_pnl) if row.unrealized_pnl is not None else None,
        )
