"""AutoPaperCloseWorker — closes expired auto-paper positions on schedule.

Expiry rules by horizon label:
  - intraday      → positions opened > 1 day ago
  - 1_3_days      → positions opened > 3 days ago
  - 3_10_days     → positions opened > 10 days ago
  - unknown/None  → positions opened > 10 days ago (conservative default)

For each expired position:
1. Mark Position.status = CLOSED, set closed_at, close_reason = "horizon_expired"
2. Compute a simple directional PnL proxy (target vs entry) and store realized_pnl
3. Commit
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import HorizonLabel, PositionStatus, SignalStatus
from app.db.models.position import Position
from app.db.models.signal import Signal
from app.db.session import SessionLocal
from app.services.persistence_signal_outcome import PersistenceSignalOutcomeService
from app.workers.base_worker import BaseWorker

_logger = logging.getLogger(__name__)

# Maximum age per horizon before a position is force-closed
_HORIZON_EXPIRY: dict[str | None, timedelta] = {
    HorizonLabel.INTRADAY.value: timedelta(days=1),
    HorizonLabel.ONE_TO_THREE_DAYS.value: timedelta(days=3),
    HorizonLabel.THREE_TO_TEN_DAYS.value: timedelta(days=10),
    None: timedelta(days=10),
}


def _resolved_expiry(horizon_value: str | None) -> timedelta:
    return _HORIZON_EXPIRY.get(horizon_value, timedelta(days=10))


def _compute_pnl_pct(position: Position, signal: Signal | None) -> float:
    """Compute a directional PnL percentage.

    Priority:
    1. ``position.close_price`` — actual broker fill price (set by IBKR adapter)
    2. ``signal.target_price`` / ``position.target_price`` — proxy when no live fill

    Returns 0.0 when data is insufficient.
    """
    if position.avg_entry_price is None:
        return 0.0
    entry = float(position.avg_entry_price)
    if entry == 0.0:
        return 0.0

    # Use the actual close price when the broker has filled the closing order.
    close = float(position.close_price) if position.close_price is not None else None
    if close is None:
        if signal is None:
            return 0.0
        close = float(signal.target_price or position.target_price or entry)

    if position.side in ("long", "buy"):
        return (close - entry) / entry
    else:
        return (entry - close) / entry


class AutoPaperCloseWorker(BaseWorker):
    """Close expired auto-paper positions based on their horizon label."""

    worker_name = "auto_paper_close"

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def execute(self) -> str:
        session = self._session or SessionLocal()
        close_session = self._session is None
        closed = 0

        try:
            now = datetime.now(UTC)
            outcome_service = PersistenceSignalOutcomeService(session)

            # Load all open auto-paper positions
            open_positions = session.execute(
                select(Position).where(
                    Position.status == PositionStatus.OPEN,
                    Position.close_reason == "auto_paper",
                )
            ).scalars().all()

            for position in open_positions:
                if position.opened_at is None:
                    continue

                # Load associated signal to get horizon_label
                signal: Signal | None = (
                    session.get(Signal, position.signal_id)
                    if position.signal_id
                    else None
                )

                horizon_value = (
                    signal.horizon_label.value if signal and signal.horizon_label else None
                )
                max_age = _resolved_expiry(horizon_value)
                age = now - position.opened_at.replace(tzinfo=UTC) if position.opened_at.tzinfo is None else now - position.opened_at

                if age < max_age:
                    continue  # not yet expired

                pnl_pct = _compute_pnl_pct(position, signal)

                position.status = PositionStatus.CLOSED
                position.closed_at = now
                position.close_reason = "horizon_expired"
                position.realized_pnl = Decimal(str(round(pnl_pct, 6)))
                # Only write close_price proxy when no real fill price was recorded
                if position.close_price is None:
                    position.close_price = position.target_price

                if signal is not None:
                    signal.signal_status = SignalStatus.CLOSED
                    outcome_service.persist_outcome(signal, position)

                closed += 1
                _logger.info(
                    "auto_paper_close: closed position for signal %s (horizon=%s, pnl=%.4f%%)",
                    position.signal_id,
                    horizon_value,
                    pnl_pct * 100,
                )

            session.commit()
        except Exception as exc:
            session.rollback()
            _logger.error("auto_paper_close fatal error: %s", exc)
            return f"auto_paper_close: fatal error — {exc}"
        finally:
            if close_session:
                session.close()

        return f"auto_paper_close: {closed} position(s) closed"
