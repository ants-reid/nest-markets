"""Phase 9 — labeling service tests."""

from __future__ import annotations

import pytest

from apps.learning.services.labeling.traded_outcome_labeler import (
    TradedOutcomeLabeler, TradeRecord,
)
from apps.learning.services.labeling.missed_opportunity_labeler import (
    MissedOpportunityLabeler, MissedOpportunityRecord,
)
from apps.learning.services.labeling.blocked_opportunity_labeler import (
    BlockedOpportunityLabeler, BlockedOpportunityRecord,
)
from apps.learning.services.labeling.forward_return_labeler import ForwardReturnLabeler
from apps.learning.services.labeling.execution_quality_labeler import (
    ExecutionQualityLabeler, ExecutionQualityRecord,
)


# ---------------------------------------------------------------------------
# TradedOutcomeLabeler
# ---------------------------------------------------------------------------

class TestTradedOutcomeLabeler:
    def _make_trade(self, entry, exit_p, side="long", qty=100.0):
        return TradeRecord(
            trade_id="t1", symbol="AAPL",
            entry_price=entry, exit_price=exit_p,
            side=side, quantity=qty,
        )

    def test_winning_long_trade(self):
        label = TradedOutcomeLabeler().label(self._make_trade(100, 110))
        assert label.outcome == "win"
        assert label.pnl == pytest.approx(1000.0)

    def test_losing_short_trade(self):
        trade = self._make_trade(100, 110, side="short")
        label = TradedOutcomeLabeler().label(trade)
        assert label.outcome == "loss"
        assert label.pnl < 0

    def test_breakeven_trade(self):
        label = TradedOutcomeLabeler().label(self._make_trade(100, 100))
        assert label.outcome == "breakeven"

    def test_r_multiple_computed(self):
        label = TradedOutcomeLabeler().label(self._make_trade(100, 102), initial_risk=200.0)
        assert label.r_multiple == pytest.approx(1.0)

    def test_r_multiple_none_when_no_risk(self):
        label = TradedOutcomeLabeler().label(self._make_trade(100, 105))
        assert label.r_multiple is None

    def test_batch_label(self):
        trades = [self._make_trade(100, 110), self._make_trade(100, 90)]
        labels = TradedOutcomeLabeler().label_batch(trades)
        assert len(labels) == 2
        assert labels[0].outcome == "win"
        assert labels[1].outcome == "loss"


# ---------------------------------------------------------------------------
# MissedOpportunityLabeler
# ---------------------------------------------------------------------------

class TestMissedOpportunityLabeler:
    def test_large_miss_long(self):
        record = MissedOpportunityRecord(
            opportunity_id="op1", symbol="NVDA",
            signal_price=100, peak_price=110,
            side="long", reason_missed="blocked_by_risk",
        )
        label = MissedOpportunityLabeler().label(record)
        assert label.missed_regime == "large_miss"
        assert label.forgone_pnl_pct == pytest.approx(0.10)

    def test_negligible_miss(self):
        record = MissedOpportunityRecord(
            opportunity_id="op2", symbol="SPY",
            signal_price=100, peak_price=100.5,
            side="long", reason_missed="no_position",
        )
        label = MissedOpportunityLabeler().label(record)
        assert label.missed_regime == "negligible"


# ---------------------------------------------------------------------------
# BlockedOpportunityLabeler
# ---------------------------------------------------------------------------

class TestBlockedOpportunityLabeler:
    def test_blocked_would_have_won(self):
        record = BlockedOpportunityRecord(
            opportunity_id="b1", symbol="TSLA",
            block_reason="max_positions",
            score_at_block=0.75,
            would_have_won=True,
        )
        label = BlockedOpportunityLabeler().label(record)
        assert label.block_quality == "missed_win"

    def test_blocked_avoided_loss(self):
        record = BlockedOpportunityRecord(
            opportunity_id="b2", symbol="META",
            block_reason="daily_loss_limit",
            score_at_block=0.55,
            would_have_won=False,
        )
        label = BlockedOpportunityLabeler().label(record)
        assert label.block_quality == "avoided_loss"

    def test_unknown_outcome(self):
        record = BlockedOpportunityRecord(
            opportunity_id="b3", symbol="AMZN",
            block_reason="risk_filter",
            score_at_block=0.80,
            would_have_won=None,
        )
        label = BlockedOpportunityLabeler().label(record)
        assert label.block_quality == "unknown"


# ---------------------------------------------------------------------------
# ForwardReturnLabeler
# ---------------------------------------------------------------------------

class TestForwardReturnLabeler:
    def test_positive_forward_return(self):
        labeler = ForwardReturnLabeler(win_threshold=0.02)
        prices = [100.0, 101.0, 103.0, 105.0, 108.0]
        label = labeler.label("sig1", prices, holding_period=4)
        assert label is not None
        assert label.forward_return == pytest.approx(0.08)
        assert label.hit is True

    def test_insufficient_data_returns_none(self):
        labeler = ForwardReturnLabeler()
        assert labeler.label("sig2", [100.0, 101.0], holding_period=5) is None

    def test_short_side_positive_return(self):
        labeler = ForwardReturnLabeler(win_threshold=0.02)
        prices = [100.0, 98.0, 95.0]
        label = labeler.label("sig3", prices, holding_period=2, side="short")
        assert label is not None
        assert label.forward_return == pytest.approx(0.05)
        assert label.hit is True


# ---------------------------------------------------------------------------
# ExecutionQualityLabeler
# ---------------------------------------------------------------------------

class TestExecutionQualityLabeler:
    def test_favourable_fill_long(self):
        record = ExecutionQualityRecord(
            trade_id="eq1", signal_price=100.0, fill_price=99.80, side="long"
        )
        label = ExecutionQualityLabeler().label(record)
        assert label.slippage_direction == "favourable"

    def test_adverse_fill_long(self):
        record = ExecutionQualityRecord(
            trade_id="eq2", signal_price=100.0, fill_price=100.50, side="long"
        )
        label = ExecutionQualityLabeler().label(record)
        assert label.slippage_direction == "adverse"
        assert label.quality_grade in {"acceptable", "poor"}

    def test_excellent_fill(self):
        record = ExecutionQualityRecord(
            trade_id="eq3", signal_price=100.0, fill_price=100.03, side="long"
        )
        label = ExecutionQualityLabeler().label(record)
        assert label.quality_grade in {"excellent", "good"}

    def test_zero_signal_price_raises(self):
        with pytest.raises(ValueError):
            ExecutionQualityLabeler().label(
                ExecutionQualityRecord(trade_id="eq4", signal_price=0, fill_price=10, side="long")
            )
