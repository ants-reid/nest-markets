"""Tests for the controlled auto-paper exception to the auto-trading block.

These tests pin the narrow allowance that lets the existing
AutoPaperTraderWorker reach the broker submit path under strictly
controlled paper-only conditions, while keeping live/uncontrolled auto
blocked.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.trading_control_service import (
    AutoTradingBlockedError,
    LiveTradingNotArmedError,
    assert_order_submission_allowed,
    is_controlled_auto_paper_allowed,
)


_CONTROLLED_ENV: dict[str, str] = {
    "AUTO_PAPER_ENABLED": "true",
    "AUTO_PAPER_MAX_ORDERS_PER_RUN": "1",
    "AUTO_PAPER_MAX_ORDERS_PER_DAY": "1",
    "AUTO_PAPER_MAX_NOTIONAL_USD": "100",
    "AUTO_PAPER_SYMBOL_ALLOWLIST": "AAPL",
    "AUTO_PAPER_ORDER_TYPE": "LIMIT",
    "AUTO_PAPER_LIMIT_PRICE": "50.00",
    "AUTO_PAPER_REQUIRE_TWS": "true",
    "BROKER_PROVIDER": "tws",
    "TWS_ENABLED": "true",
    "BROKER_MODE": "paper",
    "LIVE_EXECUTION_ENABLED": "false",
    "PAPER_TRADING_ENABLED": "true",
    "IBKR_ACCOUNT_TYPE": "paper",
}


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _apply_controlled(monkeypatch, **overrides: str) -> None:
    env = {**_CONTROLLED_ENV, **overrides}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Default posture: blocked
# ---------------------------------------------------------------------------


def test_default_posture_blocks_auto_submit():
    assert is_controlled_auto_paper_allowed() is False
    with pytest.raises(AutoTradingBlockedError):
        assert_order_submission_allowed(intent="auto")


def test_default_posture_allows_manual_paper():
    # Sanity: manual paper submission unaffected.
    assert_order_submission_allowed(intent="manual")


# ---------------------------------------------------------------------------
# Controlled config: allowed
# ---------------------------------------------------------------------------


def test_controlled_config_allows_auto_submit(monkeypatch):
    _apply_controlled(monkeypatch)
    assert is_controlled_auto_paper_allowed() is True
    # Must NOT raise — the auto path is allowed to reach the broker submit path.
    assert_order_submission_allowed(intent="auto")


# ---------------------------------------------------------------------------
# Individual env disablers — each MUST block again
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override",
    [
        {"AUTO_PAPER_ENABLED": "false"},
        {"LIVE_EXECUTION_ENABLED": "true", "BROKER_MODE": "live", "IBKR_ACCOUNT_TYPE": "live"},
        {"BROKER_MODE": "live", "IBKR_ACCOUNT_TYPE": "live"},
        {"BROKER_PROVIDER": "ibkr"},
        {"TWS_ENABLED": "false"},
        {"AUTO_PAPER_REQUIRE_TWS": "false"},
        {"AUTO_PAPER_ORDER_TYPE": "MARKET"},
        {"AUTO_PAPER_MAX_ORDERS_PER_RUN": "2"},
        {"AUTO_PAPER_MAX_ORDERS_PER_DAY": "5"},
        {"AUTO_PAPER_MAX_ORDERS_PER_RUN": "0"},
        {"AUTO_PAPER_MAX_ORDERS_PER_DAY": "0"},
        {"AUTO_PAPER_MAX_NOTIONAL_USD": "1000"},
        {"AUTO_PAPER_MAX_NOTIONAL_USD": "0"},
        {"AUTO_PAPER_SYMBOL_ALLOWLIST": ""},
        {"PAPER_TRADING_ENABLED": "false"},
    ],
    ids=[
        "AUTO_PAPER_ENABLED_false",
        "LIVE_EXECUTION_ENABLED_true",
        "BROKER_MODE_live",
        "BROKER_PROVIDER_non_tws",
        "TWS_ENABLED_false",
        "AUTO_PAPER_REQUIRE_TWS_false",
        "AUTO_PAPER_ORDER_TYPE_MARKET",
        "MAX_ORDERS_PER_RUN_above_one",
        "MAX_ORDERS_PER_DAY_above_one",
        "MAX_ORDERS_PER_RUN_zero",
        "MAX_ORDERS_PER_DAY_zero",
        "MAX_NOTIONAL_above_cap",
        "MAX_NOTIONAL_zero",
        "SYMBOL_ALLOWLIST_empty",
        "PAPER_TRADING_ENABLED_false",
    ],
)
def test_controlled_config_disablers_block(monkeypatch, override):
    _apply_controlled(monkeypatch, **override)
    assert is_controlled_auto_paper_allowed() is False
    # Live override goes through the manual-live path; everything else falls
    # back to the unconditional auto block.
    if override.get("BROKER_MODE") == "live":
        return
    with pytest.raises(AutoTradingBlockedError):
        assert_order_submission_allowed(intent="auto")


# ---------------------------------------------------------------------------
# Live trading still locked even when AUTO_PAPER_ENABLED=true
# ---------------------------------------------------------------------------


def test_live_submit_still_blocked_when_auto_paper_enabled(monkeypatch):
    _apply_controlled(
        monkeypatch,
        BROKER_MODE="live",
        IBKR_ACCOUNT_TYPE="live",
        LIVE_EXECUTION_ENABLED="true",
    )
    # Controlled gate must NOT activate for live.
    assert is_controlled_auto_paper_allowed() is False
    # Manual live still blocked by the existing live-arming guard.
    with pytest.raises(LiveTradingNotArmedError):
        assert_order_submission_allowed(intent="manual")
    # Auto under live config must still hit the unconditional block.
    with pytest.raises(AutoTradingBlockedError):
        assert_order_submission_allowed(intent="auto")


# ---------------------------------------------------------------------------
# Drift-lock guard: assert_auto_trading_allowed body must remain a single raise
# ---------------------------------------------------------------------------


def test_assert_auto_trading_allowed_body_unchanged_one_raise():
    """The inner unconditional block must remain a single raise — the
    controlled exception is implemented by the OUTER router, not by
    weakening this guard."""
    import ast
    import inspect

    from app.services.trading_control_service import assert_auto_trading_allowed

    src = inspect.getsource(assert_auto_trading_allowed)
    tree = ast.parse(src)
    func = tree.body[0]
    body = list(func.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    assert len(body) == 1
    assert isinstance(body[0], ast.Raise)
