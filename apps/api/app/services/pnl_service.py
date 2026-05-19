"""PnL snapshot service — record and query portfolio equity snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.pnl_snapshot import PnlSnapshot


@dataclass
class PnlSnapshotInput:
    """Typed input for recording a PnL snapshot."""

    equity: float
    cash: float | None = None
    gross_exposure: float | None = None
    net_exposure: float | None = None
    open_pnl: float | None = None
    closed_pnl: float | None = None
    drawdown_pct: float | None = None
    win_rate_rolling: float | None = None
    profit_factor_rolling: float | None = None
    metadata_json: dict[str, Any] | None = None
    snapshot_ts: datetime | None = None


@dataclass
class PnlSnapshotResult:
    """Typed result returned from PnL snapshot service."""

    id: object  # UUID
    snapshot_ts: datetime
    equity: float | None
    cash: float | None
    gross_exposure: float | None
    net_exposure: float | None
    open_pnl: float | None
    closed_pnl: float | None
    drawdown_pct: float | None
    win_rate_rolling: float | None
    profit_factor_rolling: float | None
    metadata_json: dict[str, Any] | None


class PnlService:
    """Record and retrieve portfolio equity snapshots.

    Responsibilities:
      - Record a snapshot at any point in time (called by workers or on paper-fill events).
      - Retrieve the most recent snapshot.
      - Retrieve the last N snapshots for charting.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def record_snapshot(self, inp: PnlSnapshotInput) -> PnlSnapshotResult:
        """Persist a new PnL snapshot row and return the typed result."""
        row = PnlSnapshot(
            snapshot_ts=inp.snapshot_ts or datetime.now(UTC),
            equity=inp.equity,
            cash=inp.cash,
            gross_exposure=inp.gross_exposure,
            net_exposure=inp.net_exposure,
            open_pnl=inp.open_pnl,
            closed_pnl=inp.closed_pnl,
            drawdown_pct=inp.drawdown_pct,
            win_rate_rolling=inp.win_rate_rolling,
            profit_factor_rolling=inp.profit_factor_rolling,
            metadata_json=inp.metadata_json,
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return self._to_result(row)

    def latest_snapshot(self) -> PnlSnapshotResult | None:
        """Return the most recent snapshot, or None if none exist."""
        row = (
            self._session.query(PnlSnapshot)
            .order_by(PnlSnapshot.snapshot_ts.desc())
            .first()
        )
        return self._to_result(row) if row is not None else None

    def recent_snapshots(self, limit: int = 100) -> list[PnlSnapshotResult]:
        """Return the last *limit* snapshots ordered oldest-first."""
        rows = (
            self._session.query(PnlSnapshot)
            .order_by(PnlSnapshot.snapshot_ts.desc())
            .limit(limit)
            .all()
        )
        return [self._to_result(r) for r in reversed(rows)]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_result(row: PnlSnapshot) -> PnlSnapshotResult:
        def _f(v) -> float | None:
            return float(v) if v is not None else None

        return PnlSnapshotResult(
            id=row.id,
            snapshot_ts=row.snapshot_ts,
            equity=_f(row.equity),
            cash=_f(row.cash),
            gross_exposure=_f(row.gross_exposure),
            net_exposure=_f(row.net_exposure),
            open_pnl=_f(row.open_pnl),
            closed_pnl=_f(row.closed_pnl),
            drawdown_pct=_f(row.drawdown_pct),
            win_rate_rolling=_f(row.win_rate_rolling),
            profit_factor_rolling=_f(row.profit_factor_rolling),
            metadata_json=row.metadata_json,
        )
