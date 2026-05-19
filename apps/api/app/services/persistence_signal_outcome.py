"""PersistenceSignalOutcomeService — records actual auto-paper trade outcomes.

Called by AutoPaperCloseWorker after each position is closed.
Captures the denormalised signal attributes + actual PnL for the AI learning loop.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.db.models.signal_outcome import SignalOutcome

if TYPE_CHECKING:
    from app.db.models.position import Position
    from app.db.models.signal import Signal


class PersistenceSignalOutcomeService:
    """Persist signal outcomes for AI learning."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def persist_outcome(
        self,
        signal: "Signal",
        position: "Position",
    ) -> SignalOutcome:
        """Create a SignalOutcome row from a closed position and its signal.

        Args:
            signal: The Signal DB row for the trade.
            position: The closed Position DB row.

        Returns:
            The newly created (and flushed but NOT committed) SignalOutcome row.
            The caller is responsible for committing the session.
        """
        entry_price = float(position.avg_entry_price or 0.0)
        # Prefer actual broker close price; fall back to target proxy
        close = float(position.close_price) if getattr(position, "close_price", None) is not None else None
        if close is None:
            close = float(position.target_price or position.avg_entry_price or 0.0)
        exit_price = close
        direction_correct: bool | None = None

        if entry_price and exit_price:
            if position.side in ("long", "buy"):
                direction_correct = exit_price > entry_price
            else:
                direction_correct = exit_price < entry_price

        pnl_pct = float(position.realized_pnl or 0.0)

        # R-multiple: (exit - entry) / |entry - stop|
        r_multiple: float | None = None
        stop = float(getattr(signal, "stop_price", None) or getattr(position, "stop_price", None) or 0.0)
        if entry_price and stop and abs(entry_price - stop) > 1e-10:
            signed_gain = (exit_price - entry_price) if position.side in ("long", "buy") else (entry_price - exit_price)
            r_multiple = round(signed_gain / abs(entry_price - stop), 4)

        # MAE / MFE percentages from position excursion tracking
        mae_pct: float | None = None
        mfe_pct: float | None = None
        if entry_price:
            mae_raw = getattr(position, "max_adverse_excursion", None)
            mfe_raw = getattr(position, "max_favorable_excursion", None)
            if mae_raw is not None:
                mae_pct = round(float(mae_raw) / entry_price, 6)
            if mfe_raw is not None:
                mfe_pct = round(float(mfe_raw) / entry_price, 6)

        outcome = SignalOutcome(
            signal_id=signal.id,
            asset_id=signal.asset_id,
            setup_type=signal.setup_type,
            direction=signal.direction,
            horizon_label=signal.horizon_label,
            catalyst_type=signal.catalyst_type,
            regime_at_entry=signal.regime,
            entry_price=Decimal(str(entry_price)),
            exit_price=Decimal(str(exit_price)),
            predicted_direction_correct=direction_correct,
            actual_pnl_pct=Decimal(str(round(pnl_pct, 6))),
            r_multiple=Decimal(str(r_multiple)) if r_multiple is not None else None,
            mae_pct=Decimal(str(mae_pct)) if mae_pct is not None else None,
            mfe_pct=Decimal(str(mfe_pct)) if mfe_pct is not None else None,
            closed_at=datetime.now(UTC),
        )
        self._session.add(outcome)
        self._session.flush()
        return outcome
