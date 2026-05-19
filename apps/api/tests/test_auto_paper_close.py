"""Tests for AutoPaperCloseWorker — QA-215."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.db.enums import HorizonLabel, PositionStatus, SignalStatus
from app.db.models.position import Position
from app.db.models.signal import Signal
from app.workers.auto_paper_close_worker import AutoPaperCloseWorker, _compute_pnl_pct, _resolved_expiry
from app.workers.base_worker import BaseWorker


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------


def _make_position(
    opened_at: datetime,
    side: str = "long",
    entry: float = 1.080,
    target: float = 1.085,
    stop: float = 1.079,
    close_price: float | None = None,
) -> MagicMock:
    p = MagicMock(spec=Position)
    p.id = uuid.uuid4()
    p.signal_id = uuid.uuid4()
    p.status = PositionStatus.OPEN
    p.close_reason = "auto_paper"
    p.opened_at = opened_at
    p.avg_entry_price = Decimal(str(entry))
    p.target_price = Decimal(str(target))
    p.stop_price = Decimal(str(stop))
    p.side = side
    p.close_price = Decimal(str(close_price)) if close_price is not None else None
    return p


def _make_signal(horizon: HorizonLabel | None = HorizonLabel.INTRADAY) -> MagicMock:
    s = MagicMock(spec=Signal)
    s.id = uuid.uuid4()
    s.horizon_label = horizon
    s.target_price = Decimal("1.0850")
    s.stop_price = Decimal("1.0790")
    s.signal_status = SignalStatus.PAPER_SUBMITTED
    return s


# ---------------------------------------------------------------------------
# QA-215 — AutoPaperCloseWorker
# ---------------------------------------------------------------------------


def test_auto_paper_close_worker_is_base_worker():
    """AutoPaperCloseWorker must extend BaseWorker."""
    assert issubclass(AutoPaperCloseWorker, BaseWorker)


def test_auto_paper_close_worker_name():
    """worker_name must be 'auto_paper_close'."""
    assert AutoPaperCloseWorker.worker_name == "auto_paper_close"


def test_resolved_expiry_intraday():
    """Intraday horizon expires in 1 day."""
    assert _resolved_expiry(HorizonLabel.INTRADAY.value) == timedelta(days=1)


def test_resolved_expiry_3_10_days():
    """3_10_days horizon expires in 10 days."""
    assert _resolved_expiry(HorizonLabel.THREE_TO_TEN_DAYS.value) == timedelta(days=10)


def test_resolved_expiry_unknown_defaults_to_10():
    """Unknown horizon defaults to 10-day expiry."""
    assert _resolved_expiry(None) == timedelta(days=10)


def test_compute_pnl_pct_long_positive():
    """Long position where target > entry should return positive PnL %."""
    position = _make_position(datetime.now(UTC), side="long", entry=1.080, target=1.085)
    signal = _make_signal()
    signal.target_price = Decimal("1.085")
    pnl = _compute_pnl_pct(position, signal)
    assert pnl > 0


def test_compute_pnl_pct_returns_zero_without_signal():
    """Returns 0 when signal is None."""
    position = _make_position(datetime.now(UTC))
    assert _compute_pnl_pct(position, None) == 0.0


def test_close_worker_closes_expired_intraday_position():
    """Worker closes intraday positions opened more than 1 day ago."""
    mock_session = MagicMock()
    opened_2_days_ago = datetime.now(UTC) - timedelta(days=2)

    position = _make_position(opened_2_days_ago)
    signal = _make_signal(HorizonLabel.INTRADAY)

    mock_session.execute.return_value.scalars.return_value.all.return_value = [position]
    mock_session.get.return_value = signal

    worker = AutoPaperCloseWorker(session=mock_session)
    result = worker.run()

    assert result.status == "ok"
    assert "1 position(s) closed" in result.message
    assert position.status == PositionStatus.CLOSED
    assert position.close_reason == "horizon_expired"
    assert signal.signal_status == SignalStatus.CLOSED


def test_close_worker_does_not_close_fresh_position():
    """Worker does not close a position within its horizon window."""
    mock_session = MagicMock()
    opened_1_hour_ago = datetime.now(UTC) - timedelta(hours=1)

    position = _make_position(opened_1_hour_ago)
    signal = _make_signal(HorizonLabel.INTRADAY)  # expires after 1 day

    mock_session.execute.return_value.scalars.return_value.all.return_value = [position]
    mock_session.get.return_value = signal

    worker = AutoPaperCloseWorker(session=mock_session)
    result = worker.run()

    assert result.status == "ok"
    assert "0 position(s) closed" in result.message
    assert position.status == PositionStatus.OPEN


def test_close_worker_handles_no_open_positions():
    """Worker exits cleanly when no open auto-paper positions exist."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalars.return_value.all.return_value = []

    worker = AutoPaperCloseWorker(session=mock_session)
    result = worker.run()

    assert result.status == "ok"
    assert "0 position(s) closed" in result.message


def test_close_worker_mixed_horizons():
    """Worker selectively closes only expired positions among mixed horizons."""
    mock_session = MagicMock()

    expired_pos = _make_position(datetime.now(UTC) - timedelta(days=2))  # intraday, expired
    fresh_pos = _make_position(datetime.now(UTC) - timedelta(hours=12))  # intraday, still valid

    expired_signal = _make_signal(HorizonLabel.INTRADAY)
    fresh_signal = _make_signal(HorizonLabel.INTRADAY)

    mock_session.execute.return_value.scalars.return_value.all.return_value = [expired_pos, fresh_pos]

    def get_signal(model, sig_id):
        if sig_id == expired_pos.signal_id:
            return expired_signal
        return fresh_signal

    mock_session.get.side_effect = get_signal

    worker = AutoPaperCloseWorker(session=mock_session)
    result = worker.run()

    assert "1 position(s) closed" in result.message
    assert expired_pos.status == PositionStatus.CLOSED
    assert fresh_pos.status == PositionStatus.OPEN


# ---------------------------------------------------------------------------
# P1 fix: close_price priority over target proxy
# ---------------------------------------------------------------------------


def test_compute_pnl_pct_uses_close_price_when_set():
    """_compute_pnl_pct must use close_price over target_price when close_price is set."""
    position = _make_position(
        datetime.now(UTC),
        side="long",
        entry=1.080,
        target=1.090,     # proxy would give a large gain
        close_price=1.081,  # actual fill — small gain
    )
    pnl = _compute_pnl_pct(position, None)
    # Should reflect the real fill, not the optimistic target
    assert pytest.approx(pnl, rel=1e-4) == (1.081 - 1.080) / 1.080


def test_compute_pnl_pct_falls_back_to_target_when_close_price_none():
    """_compute_pnl_pct falls back to target proxy when close_price is None."""
    position = _make_position(
        datetime.now(UTC),
        side="long",
        entry=1.080,
        target=1.085,
        close_price=None,
    )
    signal = _make_signal()
    signal.target_price = Decimal("1.085")
    pnl = _compute_pnl_pct(position, signal)
    assert pytest.approx(pnl, rel=1e-4) == (1.085 - 1.080) / 1.080


def test_close_worker_preserves_real_close_price():
    """Worker does not overwrite close_price when it was already set by the broker."""
    mock_session = MagicMock()
    opened_2_days_ago = datetime.now(UTC) - timedelta(days=2)
    position = _make_position(opened_2_days_ago, close_price=1.082)  # broker fill already set
    signal = _make_signal(HorizonLabel.INTRADAY)

    mock_session.execute.return_value.scalars.return_value.all.return_value = [position]
    mock_session.get.return_value = signal

    AutoPaperCloseWorker(session=mock_session).run()

    # close_price must remain the broker fill value, not overwritten
    assert float(position.close_price) == pytest.approx(1.082)
