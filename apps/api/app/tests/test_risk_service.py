from app.services.execution_mode_service import ExecutionModeService
from app.services.risk_profile_service import RiskProfile
from app.services.risk_service import RiskContext, RiskService
from app.services.signal_service import SignalOutput


def _signal() -> SignalOutput:
    return SignalOutput(
        asset="EURUSD",
        timeframe="1h",
        direction="long",
        regime="trend",
        setup_type="trend_pullback",
        entry_zone=(1.081, 1.082),
        stop_price=1.078,
        target_price=1.088,
        confidence=0.75,
        horizon_label="1_3_days",
        catalyst_type="macro",
        catalyst_score=0.6,
        catalyst_summary="Macro tailwind",
        thesis="Structure supports continuation",
        invalidators=["Break below structure"],
        signal_score=75.0,
        should_trade=True,
    )


def _context() -> RiskContext:
    return RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )


def _service() -> RiskService:
    profile = RiskProfile()
    return RiskService(profile=profile, execution_mode_service=ExecutionModeService())


def test_blocks_on_confidence_threshold() -> None:
    signal = _signal()
    signal = SignalOutput(**{**signal.__dict__, "confidence": 0.4})

    decision = _service().evaluate(signal, _context())

    assert decision.approved is False
    assert "confidence_below_threshold" in decision.blocked_reasons


def test_blocks_on_signal_score_threshold() -> None:
    signal = _signal()
    signal = SignalOutput(**{**signal.__dict__, "signal_score": 40.0})

    decision = _service().evaluate(signal, _context())

    assert decision.approved is False
    assert "signal_score_below_threshold" in decision.blocked_reasons


def test_blocks_on_spread_cap() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "spread_bps": 40.0})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "spread_above_cap" in decision.blocked_reasons


def test_blocks_on_drawdown() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "daily_drawdown_pct": 2.5})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "daily_drawdown_exceeded" in decision.blocked_reasons


def test_blocks_on_cooldown() -> None:
    context = _context()
    context = RiskContext(
        **{
            **context.__dict__,
            "consecutive_losses": 3,
            "minutes_since_last_loss": 60,
        }
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "cooldown_active" in decision.blocked_reasons


def test_blocks_on_cooldown_when_minutes_since_last_loss_is_none() -> None:
    context = _context()
    context = RiskContext(
        **{
            **context.__dict__,
            "consecutive_losses": 3,
            "minutes_since_last_loss": None,
        }
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "cooldown_active" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"


def test_allows_when_cooldown_threshold_has_expired() -> None:
    context = _context()
    context = RiskContext(
        **{
            **context.__dict__,
            "consecutive_losses": 3,
            "minutes_since_last_loss": 180,
        }
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is True
    assert "cooldown_active" not in decision.blocked_reasons
    assert decision.selected_execution_mode == "paper"


def test_allows_when_consecutive_losses_below_threshold_with_null_minutes() -> None:
    context = _context()
    context = RiskContext(
        **{
            **context.__dict__,
            "consecutive_losses": 2,
            "minutes_since_last_loss": None,
        }
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is True
    assert "cooldown_active" not in decision.blocked_reasons
    assert decision.selected_execution_mode == "paper"


def test_blocks_when_market_quality_flag_is_false() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "market_quality_flag": False})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "market_quality_bad" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"


def test_blocks_on_correlated_exposure() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "correlated_exposure_count": 2})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "correlated_exposure_exceeded" in decision.blocked_reasons


def test_blocks_when_session_not_allowed() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "session_allowed": False})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "session_not_allowed" in decision.blocked_reasons


def test_blocks_when_kill_switch_active() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "kill_switch_active": True})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "kill_switch_active" in decision.blocked_reasons


def test_blocks_when_open_positions_cap_reached() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "open_positions_count": 6})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "max_open_positions_exceeded" in decision.blocked_reasons


def test_blocks_when_should_trade_is_false() -> None:
    signal = _signal()
    signal = SignalOutput(**{**signal.__dict__, "should_trade": False})

    decision = _service().evaluate(signal, _context())

    assert decision.approved is False
    assert "signal_not_actionable" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_blocks_when_direction_is_flat() -> None:
    signal = _signal()
    signal = SignalOutput(**{**signal.__dict__, "direction": "flat"})

    decision = _service().evaluate(signal, _context())

    assert decision.approved is False
    assert "signal_not_actionable" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_blocks_when_account_equity_is_zero() -> None:
    context = _context()
    context = RiskContext(**{**context.__dict__, "account_equity": 0.0})

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "capital_or_risk_limit_block" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_blocks_with_multiple_reasons_when_should_trade_is_false_and_spread_above_cap() -> None:
    signal = _signal()
    signal = SignalOutput(**{**signal.__dict__, "should_trade": False})

    context = _context()
    context = RiskContext(**{**context.__dict__, "spread_bps": 40.0})

    decision = _service().evaluate(signal, context)

    assert decision.approved is False
    assert "signal_not_actionable" in decision.blocked_reasons
    assert "spread_above_cap" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_blocks_with_multiple_reasons_when_session_not_allowed_and_kill_switch_active() -> None:
    context = _context()
    context = RiskContext(
        **{**context.__dict__, "session_allowed": False, "kill_switch_active": True}
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "session_not_allowed" in decision.blocked_reasons
    assert "kill_switch_active" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_blocks_with_multiple_reasons_when_daily_drawdown_exceeded_and_cooldown_active() -> None:
    context = _context()
    context = RiskContext(
        **{
            **context.__dict__,
            "daily_drawdown_pct": 2.5,
            "consecutive_losses": 3,
            "minutes_since_last_loss": 60,
        }
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "daily_drawdown_exceeded" in decision.blocked_reasons
    assert "cooldown_active" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_blocks_with_multiple_reasons_when_max_positions_exceeded_and_correlated_exposure_exceeded() -> None:
    context = _context()
    context = RiskContext(
        **{
            **context.__dict__,
            "open_positions_count": 6,
            "correlated_exposure_count": 2,
        }
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "max_open_positions_exceeded" in decision.blocked_reasons
    assert "correlated_exposure_exceeded" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_blocks_with_multiple_reasons_when_session_not_allowed_kill_switch_active_and_max_positions_exceeded() -> None:
    context = _context()
    context = RiskContext(
        **{
            **context.__dict__,
            "session_allowed": False,
            "kill_switch_active": True,
            "open_positions_count": 6,
        }
    )

    decision = _service().evaluate(_signal(), context)

    assert decision.approved is False
    assert "session_not_allowed" in decision.blocked_reasons
    assert "kill_switch_active" in decision.blocked_reasons
    assert "max_open_positions_exceeded" in decision.blocked_reasons
    assert decision.selected_execution_mode == "blocked"
    assert decision.allowed_risk_amount == 0.0


def test_successful_approval() -> None:
    decision = _service().evaluate(_signal(), _context())

    assert decision.approved is True
    assert decision.blocked_reasons == []
    assert decision.allowed_risk_amount > 0
    assert decision.selected_execution_mode == "paper"
