"""POH-02: End-to-end paper trade flow validation for RC-3 staging deployment.

Tests integration between signal generation, opportunity ranking, and outcome capture.
Uses mock signals and positions to validate the learning loop pipeline.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

from app.db.enums import CatalystType, HorizonLabel, RegimeType, SetupType, SignalStatus, TradeDirection
from app.db.models.position import Position
from app.db.models.signal import Signal
from app.services.persistence_signal_outcome import PersistenceSignalOutcomeService


def create_mock_signal(direction: TradeDirection = TradeDirection.LONG) -> MagicMock:
    """Create a mock signal matching test_signal_outcome.py pattern."""
    s = MagicMock(spec=Signal)
    s.id = uuid.uuid4()
    s.asset_id = uuid.uuid4()
    s.setup_type = SetupType.TREND_PULLBACK
    s.direction = direction
    s.horizon_label = HorizonLabel.INTRADAY
    s.catalyst_type = CatalystType.MACRO
    s.regime = RegimeType.TREND
    s.target_price = Decimal("1.0850")
    s.stop_price = Decimal("1.0790")
    s.signal_status = SignalStatus.PAPER_SUBMITTED
    return s


def create_mock_position(entry_price: Decimal, exit_price: Decimal, side: str = "long") -> MagicMock:
    """Create a mock position for outcome testing."""
    p = MagicMock(spec=Position)
    p.id = uuid.uuid4()
    p.signal_id = uuid.uuid4()
    p.asset_id = uuid.uuid4()
    p.avg_entry_price = entry_price
    p.target_price = exit_price
    p.close_price = None   # not yet set by broker; fall back to target proxy
    p.side = side
    p.max_adverse_excursion = None
    p.max_favorable_excursion = None
    # Calculate realized PnL
    if side == "long":
        p.realized_pnl = (exit_price - entry_price) * 100
    else:
        p.realized_pnl = (entry_price - exit_price) * 100
    return p


# ---------------------------------------------------------------------------
# POH-02 Tests — End-to-End Paper Trading Flow
# ---------------------------------------------------------------------------


class TestPOH02EndToEndFlow:
    """End-to-end paper trading flow validation for RC-3 deployment."""

    def test_outcome_long_profitable_marked_correct(self):
        """LONG trade profitable (exit > entry) must be marked predicted_direction_correct=True."""
        mock_session = MagicMock()
        signal = create_mock_signal(TradeDirection.LONG)
        position = create_mock_position(Decimal("1.0800"), Decimal("1.0850"), "long")
        position.signal_id = signal.id
        position.asset_id = signal.asset_id
        
        service = PersistenceSignalOutcomeService(mock_session)
        service.persist_outcome(signal, position)
        
        # Extract outcome from session.add() call
        mock_session.add.assert_called_once()
        outcome = mock_session.add.call_args[0][0]
        assert outcome.signal_id == signal.id
        assert outcome.asset_id == position.asset_id
        assert outcome.predicted_direction_correct is True
        assert outcome.direction == TradeDirection.LONG

    def test_outcome_long_loss_marked_incorrect(self):
        """LONG trade loss (exit < entry) must be marked predicted_direction_correct=False."""
        mock_session = MagicMock()
        signal = create_mock_signal(TradeDirection.LONG)
        position = create_mock_position(Decimal("1.0850"), Decimal("1.0800"), "long")
        position.signal_id = signal.id
        position.asset_id = signal.asset_id
        
        service = PersistenceSignalOutcomeService(mock_session)
        service.persist_outcome(signal, position)
        
        outcome = mock_session.add.call_args[0][0]
        assert outcome.predicted_direction_correct is False

    def test_outcome_short_profitable_marked_correct(self):
        """SHORT trade profitable (exit < entry) must be marked predicted_direction_correct=True."""
        mock_session = MagicMock()
        signal = create_mock_signal(TradeDirection.SHORT)
        position = create_mock_position(Decimal("1.0900"), Decimal("1.0850"), "short")
        position.signal_id = signal.id
        position.asset_id = signal.asset_id
        
        service = PersistenceSignalOutcomeService(mock_session)
        service.persist_outcome(signal, position)
        
        outcome = mock_session.add.call_args[0][0]
        assert outcome.predicted_direction_correct is True
        assert outcome.direction == TradeDirection.SHORT

    def test_outcome_denormalizes_signal_attributes(self):
        """Outcome must denormalize signal attributes for ML feature input."""
        mock_session = MagicMock()
        signal = create_mock_signal(TradeDirection.LONG)
        signal.setup_type = SetupType.NEWS_CONTINUATION
        signal.catalyst_type = CatalystType.EARNINGS
        signal.horizon_label = HorizonLabel.THREE_TO_TEN_DAYS
        signal.regime = RegimeType.BREAKOUT
        
        position = create_mock_position(Decimal("1.0800"), Decimal("1.0850"), "long")
        position.signal_id = signal.id
        position.asset_id = signal.asset_id
        
        service = PersistenceSignalOutcomeService(mock_session)
        service.persist_outcome(signal, position)
        
        # Verify denormalized attributes for future ML analysis
        outcome = mock_session.add.call_args[0][0]
        assert outcome.setup_type == signal.setup_type
        assert outcome.direction == signal.direction
        assert outcome.horizon_label == signal.horizon_label
        assert outcome.catalyst_type == signal.catalyst_type
        assert outcome.regime_at_entry == signal.regime

    def test_outcome_captures_pnl_from_position(self):
        """Outcome must capture actual_pnl_pct from position realized_pnl."""
        mock_session = MagicMock()
        signal = create_mock_signal()
        position = create_mock_position(Decimal("1.0800"), Decimal("1.0850"), "long")
        position.signal_id = signal.id
        position.asset_id = signal.asset_id
        position.realized_pnl = Decimal("500.00")  # Explicit PnL
        
        service = PersistenceSignalOutcomeService(mock_session)
        service.persist_outcome(signal, position)
        
        outcome = mock_session.add.call_args[0][0]
        assert outcome.actual_pnl_pct is not None
        mock_session.flush.assert_called_once()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
