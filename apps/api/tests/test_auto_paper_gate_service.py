"""Unit tests for AutoPaperGateService (Auto Paper v1 controlled-run gates)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.auto_paper_gate_service import (
    AutoPaperGateDecision,
    AutoPaperGateService,
)


def _settings(**overrides):
    base = dict(
        auto_paper_enabled=True,
        auto_paper_max_orders_per_run=1,
        auto_paper_max_orders_per_day=1,
        auto_paper_max_notional_usd=100.0,
        auto_paper_symbol_allowlist="AAPL",
        auto_paper_order_type="LIMIT",
        auto_paper_limit_price=50.0,
        auto_paper_require_tws=True,
        broker_provider="tws",
        broker_mode="paper",
        tws_enabled=True,
        live_execution_enabled=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _session_with(*, kill_switch: bool, orders_today: int = 0):
    """Build a MagicMock Session that returns the supplied gate inputs."""
    session = MagicMock()
    # count_orders_today reads via session.execute().scalar_one()
    scalar = MagicMock()
    scalar.scalar_one.return_value = orders_today
    session.execute.return_value = scalar
    # _kill_switch_active reads via session.query(...).filter(...).first()
    profile = SimpleNamespace(kill_switch_enabled=kill_switch)
    session.query.return_value.filter.return_value.first.return_value = profile
    return session


# ---------------------------------------------------------------------------
# Run-level evaluation
# ---------------------------------------------------------------------------


def test_evaluate_run_blocks_when_auto_paper_disabled():
    svc = AutoPaperGateService(_settings(auto_paper_enabled=False))
    decision = svc.evaluate_run(_session_with(kill_switch=False))
    assert decision.allowed is False
    assert decision.blocking_gate == "auto_paper_enabled"


def test_evaluate_run_blocks_when_live_execution_enabled():
    svc = AutoPaperGateService(_settings(live_execution_enabled=True))
    decision = svc.evaluate_run(_session_with(kill_switch=False))
    assert decision.allowed is False
    assert decision.blocking_gate == "live_execution_enabled"


def test_evaluate_run_blocks_when_broker_mode_not_paper():
    svc = AutoPaperGateService(_settings(broker_mode="live"))
    decision = svc.evaluate_run(_session_with(kill_switch=False))
    assert decision.allowed is False
    assert decision.blocking_gate == "broker_mode"


def test_evaluate_run_blocks_when_broker_provider_not_tws():
    svc = AutoPaperGateService(_settings(broker_provider="ibkr"))
    decision = svc.evaluate_run(_session_with(kill_switch=False))
    assert decision.allowed is False
    assert decision.blocking_gate == "broker_provider"


def test_evaluate_run_blocks_when_tws_disabled():
    svc = AutoPaperGateService(_settings(tws_enabled=False))
    decision = svc.evaluate_run(_session_with(kill_switch=False))
    assert decision.allowed is False
    assert decision.blocking_gate == "tws_enabled"


def test_evaluate_run_blocks_non_limit_order_type():
    svc = AutoPaperGateService(_settings(auto_paper_order_type="MARKET"))
    decision = svc.evaluate_run(_session_with(kill_switch=False))
    assert decision.allowed is False
    assert decision.blocking_gate == "order_type"


def test_evaluate_run_blocks_empty_allowlist():
    svc = AutoPaperGateService(_settings(auto_paper_symbol_allowlist=""))
    decision = svc.evaluate_run(_session_with(kill_switch=False))
    assert decision.allowed is False
    assert decision.blocking_gate == "symbol_allowlist"


def test_evaluate_run_blocks_kill_switch():
    svc = AutoPaperGateService(_settings())
    decision = svc.evaluate_run(_session_with(kill_switch=True))
    assert decision.allowed is False
    assert decision.blocking_gate == "kill_switch"


def test_evaluate_run_blocks_when_daily_cap_reached():
    svc = AutoPaperGateService(_settings(auto_paper_max_orders_per_day=1))
    decision = svc.evaluate_run(_session_with(kill_switch=False, orders_today=1))
    assert decision.allowed is False
    assert decision.blocking_gate == "max_orders_per_day"


def test_evaluate_run_allows_with_all_gates_satisfied():
    svc = AutoPaperGateService(_settings())
    decision = svc.evaluate_run(_session_with(kill_switch=False, orders_today=0))
    assert decision.allowed is True
    assert decision.blocking_gate is None


# ---------------------------------------------------------------------------
# Per-order evaluation
# ---------------------------------------------------------------------------


def test_evaluate_order_blocks_off_allowlist_symbol():
    svc = AutoPaperGateService(_settings())
    decision = svc.evaluate_order(
        symbol="MSFT",
        order_type="LIMIT",
        limit_price=Decimal("50.00"),
        quantity=Decimal("1.0"),
    )
    assert decision.allowed is False
    assert decision.blocking_gate == "symbol_allowlist"


def test_evaluate_order_blocks_market_order():
    svc = AutoPaperGateService(_settings())
    decision = svc.evaluate_order(
        symbol="AAPL",
        order_type="MARKET",
        limit_price=None,
        quantity=Decimal("1.0"),
    )
    assert decision.allowed is False
    assert decision.blocking_gate == "order_type"


def test_evaluate_order_blocks_excess_notional():
    svc = AutoPaperGateService(_settings(auto_paper_max_notional_usd=49.0))
    decision = svc.evaluate_order(
        symbol="AAPL",
        order_type="LIMIT",
        limit_price=Decimal("50.00"),
        quantity=Decimal("1.0"),
    )
    assert decision.allowed is False
    assert decision.blocking_gate == "max_notional_usd"


def test_evaluate_order_allows_limit_within_notional_on_allowlist():
    svc = AutoPaperGateService(_settings())
    decision = svc.evaluate_order(
        symbol="AAPL",
        order_type="LIMIT",
        limit_price=Decimal("50.00"),
        quantity=Decimal("1.0"),
    )
    assert decision.allowed is True
    assert decision.snapshot["notional_usd"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_reflects_settings_and_session_state():
    svc = AutoPaperGateService(_settings())
    snap = svc.snapshot(_session_with(kill_switch=True, orders_today=3))
    assert snap["auto_paper_enabled"] is True
    assert snap["broker_provider"] == "tws"
    assert snap["broker_mode"] == "paper"
    assert snap["symbol_allowlist"] == ["AAPL"]
    assert snap["order_type"] == "LIMIT"
    assert snap["limit_price"] == 50.0
    assert snap["max_notional_usd"] == 100.0
    assert snap["orders_today"] == 3
    assert snap["kill_switch_active"] is True


def test_snapshot_exposes_background_scheduler_fields_defaults():
    svc = AutoPaperGateService(_settings())
    snap = svc.snapshot()
    assert snap["background_scheduler_enabled"] is False
    assert snap["minutes_between_runs"] == 30
    assert snap["kill_on_error_count"] == 3
    assert snap["kill_on_reject_rate"] == 0.5


def test_snapshot_exposes_background_scheduler_fields_overridden():
    svc = AutoPaperGateService(
        _settings(
            auto_paper_background_scheduler_enabled=True,
            auto_paper_minutes_between_runs=15,
            auto_paper_kill_on_error_count=5,
            auto_paper_kill_on_reject_rate=0.25,
        )
    )
    snap = svc.snapshot()
    assert snap["background_scheduler_enabled"] is True
    assert snap["minutes_between_runs"] == 15
    assert snap["kill_on_error_count"] == 5
    assert snap["kill_on_reject_rate"] == 0.25


# ---------------------------------------------------------------------------
# Dataclass shape
# ---------------------------------------------------------------------------


def test_gate_decision_is_immutable():
    decision = AutoPaperGateDecision(allowed=True, blocking_gate=None, reason=None)
    with pytest.raises(Exception):
        decision.allowed = False  # type: ignore[misc]
