"""Tests for SignalOutcome model and PersistenceSignalOutcomeService — QA-216/217/218."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.db.enums import HorizonLabel, PositionStatus, SignalStatus, TradeDirection, SetupType, RegimeType, CatalystType
from app.db.models.position import Position
from app.db.models.signal import Signal
from app.db.models.signal_outcome import SignalOutcome
from app.services.persistence_signal_outcome import PersistenceSignalOutcomeService
from app.workers.auto_paper_close_worker import AutoPaperCloseWorker


# ---------------------------------------------------------------------------
# QA-216 — SignalOutcome model structure
# ---------------------------------------------------------------------------


def test_signal_outcome_is_importable():
    """SignalOutcome must be importable from app.db.models."""
    from app.db.models import SignalOutcome as SO
    assert SO is not None


def test_signal_outcome_has_required_fields():
    """SignalOutcome must define expected columns."""
    cols = {c.key for c in SignalOutcome.__table__.columns}
    required = {
        "id", "signal_id", "asset_id", "setup_type", "direction",
        "horizon_label", "catalyst_type", "regime_at_entry",
        "entry_price", "exit_price", "predicted_direction_correct",
        "actual_pnl_pct", "closed_at",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_signal_outcome_tablename():
    """SignalOutcome.__tablename__ must be 'signal_outcomes'."""
    assert SignalOutcome.__tablename__ == "signal_outcomes"


# ---------------------------------------------------------------------------
# QA-217 — PersistenceSignalOutcomeService unit tests
# ---------------------------------------------------------------------------


def _make_signal() -> MagicMock:
    s = MagicMock(spec=Signal)
    s.id = uuid.uuid4()
    s.asset_id = uuid.uuid4()
    s.setup_type = SetupType.TREND_PULLBACK
    s.direction = TradeDirection.LONG
    s.horizon_label = HorizonLabel.INTRADAY
    s.catalyst_type = CatalystType.MACRO
    s.regime = RegimeType.TREND
    s.target_price = Decimal("1.0850")
    s.stop_price = Decimal("1.0790")
    s.signal_status = SignalStatus.PAPER_SUBMITTED
    return s


def _make_position(side: str = "long") -> MagicMock:
    p = MagicMock(spec=Position)
    p.avg_entry_price = Decimal("1.0815")
    p.target_price = Decimal("1.0850")
    p.realized_pnl = Decimal("0.003241")
    p.side = side
    p.close_price = None
    p.max_adverse_excursion = None
    p.max_favorable_excursion = None
    return p


def test_persist_outcome_adds_row_to_session():
    """persist_outcome adds a SignalOutcome to the session."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    position = _make_position("long")

    service.persist_outcome(signal, position)

    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    assert isinstance(mock_session.add.call_args[0][0], SignalOutcome)


def test_persist_outcome_long_direction_correct_when_exit_above_entry():
    """Long trade: predicted_direction_correct=True when exit > entry."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    position = _make_position("long")
    position.avg_entry_price = Decimal("1.0800")
    position.target_price = Decimal("1.0850")  # exit above entry
    position.realized_pnl = Decimal("0.004629")

    service.persist_outcome(signal, position)

    outcome = mock_session.add.call_args[0][0]
    assert outcome.predicted_direction_correct is True


def test_persist_outcome_long_direction_wrong_when_exit_below_entry():
    """Long trade: predicted_direction_correct=False when exit < entry."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    position = _make_position("long")
    position.avg_entry_price = Decimal("1.0850")
    position.target_price = Decimal("1.0800")  # exit below entry (loss)
    position.realized_pnl = Decimal("-0.004608")

    service.persist_outcome(signal, position)

    outcome = mock_session.add.call_args[0][0]
    assert outcome.predicted_direction_correct is False


def test_persist_outcome_captures_pnl():
    """persist_outcome stores actual_pnl_pct from position.realized_pnl."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    position = _make_position()
    position.realized_pnl = Decimal("0.012345")

    service.persist_outcome(signal, position)

    outcome = mock_session.add.call_args[0][0]
    assert float(outcome.actual_pnl_pct) == pytest.approx(0.012345, rel=1e-4)


# ---------------------------------------------------------------------------
# QA-218 — Close worker creates outcome rows
# ---------------------------------------------------------------------------


def test_close_worker_creates_outcome_on_close():
    """AutoPaperCloseWorker must call PersistenceSignalOutcomeService on close."""
    from datetime import timedelta

    mock_session = MagicMock()
    opened_at = datetime.now(UTC) - timedelta(days=2)

    position = MagicMock(spec=Position)
    position.id = uuid.uuid4()
    position.signal_id = uuid.uuid4()
    position.status = PositionStatus.OPEN
    position.close_reason = "auto_paper"
    position.opened_at = opened_at
    position.avg_entry_price = Decimal("1.080")
    position.target_price = Decimal("1.085")
    position.stop_price = Decimal("1.079")
    position.side = "long"
    position.realized_pnl = None

    signal = _make_signal()
    signal.horizon_label = HorizonLabel.INTRADAY

    mock_session.execute.return_value.scalars.return_value.all.return_value = [position]
    mock_session.get.return_value = signal

    with patch(
        "app.workers.auto_paper_close_worker.PersistenceSignalOutcomeService"
    ) as mock_outcome_cls:
        mock_outcome_svc = MagicMock()
        mock_outcome_cls.return_value = mock_outcome_svc

        worker = AutoPaperCloseWorker(session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    mock_outcome_svc.persist_outcome.assert_called_once_with(signal, position)


# ---------------------------------------------------------------------------
# QA-219 — R-multiple, MAE%, MFE% in SignalOutcome
# ---------------------------------------------------------------------------


def test_signal_outcome_has_risk_quality_fields():
    """SignalOutcome must define r_multiple, mae_pct, mfe_pct columns."""
    cols = {c.key for c in SignalOutcome.__table__.columns}
    assert {"r_multiple", "mae_pct", "mfe_pct"}.issubset(cols)


def test_persist_outcome_computes_r_multiple_long():
    """Long trade: r_multiple = (exit - entry) / (entry - stop)."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    signal.stop_price = Decimal("1.0790")   # risk = 1.0815 - 1.0790 = 0.0025
    position = _make_position("long")
    position.avg_entry_price = Decimal("1.0815")
    position.target_price = Decimal("1.0865")   # gain = 0.0050; R = 0.0050 / 0.0025 = 2.0
    position.realized_pnl = Decimal("0.005")
    position.stop_price = Decimal("1.0790")

    service.persist_outcome(signal, position)
    outcome = mock_session.add.call_args[0][0]

    assert outcome.r_multiple is not None
    assert float(outcome.r_multiple) == pytest.approx(2.0, rel=1e-3)


def test_persist_outcome_r_multiple_none_when_no_stop():
    """r_multiple is None when stop_price is unavailable."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    signal.stop_price = None
    position = _make_position("long")
    position.stop_price = None

    service.persist_outcome(signal, position)
    outcome = mock_session.add.call_args[0][0]

    assert outcome.r_multiple is None


def test_persist_outcome_captures_mae_and_mfe():
    """persist_outcome stores mae_pct and mfe_pct from position excursion fields."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    position = _make_position("long")
    position.avg_entry_price = Decimal("1.0800")
    position.max_adverse_excursion = Decimal("0.0010")   # 0.0010 / 1.0800 ≈ 0.000926
    position.max_favorable_excursion = Decimal("0.0050")  # 0.0050 / 1.0800 ≈ 0.004630

    service.persist_outcome(signal, position)
    outcome = mock_session.add.call_args[0][0]

    assert outcome.mae_pct is not None
    assert float(outcome.mae_pct) == pytest.approx(0.0010 / 1.0800, rel=1e-4)
    assert outcome.mfe_pct is not None
    assert float(outcome.mfe_pct) == pytest.approx(0.0050 / 1.0800, rel=1e-4)


def test_persist_outcome_uses_close_price_over_target_proxy():
    """persist_outcome uses position.close_price (real fill) when set."""
    mock_session = MagicMock()
    service = PersistenceSignalOutcomeService(mock_session)

    signal = _make_signal()
    position = _make_position("long")
    position.avg_entry_price = Decimal("1.0800")
    position.target_price = Decimal("1.0900")   # optimistic proxy
    position.close_price = Decimal("1.0820")    # actual fill (small gain)
    position.realized_pnl = Decimal("0.002")

    service.persist_outcome(signal, position)
    outcome = mock_session.add.call_args[0][0]

    # exit_price should be the actual fill, not the target proxy
    assert float(outcome.exit_price) == pytest.approx(1.0820, rel=1e-5)
    assert outcome.predicted_direction_correct is True
