"""Trading control service for mode-aware order gating.

MH-36B makes the broker stack live-compatible, not live-enabled.

Current env-backed control model:
  - trading_mode: paper | live
  - execution_control: manual | auto
  - arming_state: armed | disarmed | emergency_stopped

Implementation notes for this phase:
  - Paper manual trading must keep working, so valid paper defaults resolve to
    ``armed``.
  - Live mode is visible and health-reportable, but live order submission stays
    blocked until future arming/risk/emergency-stop phases exist.
  - Auto trading is always blocked in MH-36B.
"""
from __future__ import annotations

import inspect
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.config import get_settings


class TradingControlError(Exception):
    """Base exception for trading control enforcement failures."""


class TradingControlMisconfiguredError(TradingControlError):
    """Raised when env-backed trading mode inputs do not form a valid state."""


class AutoTradingBlockedError(TradingControlError):
    """Raised when auto trading is attempted before it is supported."""


class LiveTradingNotArmedError(TradingControlError):
    """Raised when live submission is attempted before live arming exists."""


class EmergencyStopActiveError(TradingControlError):
    """Raised when trading is halted by an emergency stop."""


@dataclass(frozen=True)
class TradingControlState:
    """Derived trading control state for the current runtime."""

    trading_mode: str
    execution_control: str
    arming_state: str
    live_order_submission_allowed: bool
    paper_order_submission_allowed: bool
    auto_trading_allowed: bool
    emergency_stop_active: bool
    reasons: tuple[str, ...]


def _get_env_mode_tuple() -> tuple[bool, str, str]:
    settings = get_settings()
    return (
        settings.live_execution_enabled,
        settings.broker_mode.lower(),
        settings.ibkr_account_type.lower(),
    )


def _misconfigured_message() -> str:
    live_enabled, broker_mode, account_type = _get_env_mode_tuple()
    return (
        "Broker mode misconfigured. Got: "
        f"LIVE_EXECUTION_ENABLED={live_enabled}, "
        f"BROKER_MODE={broker_mode!r}, "
        f"IBKR_ACCOUNT_TYPE={account_type!r}. "
        "Valid combinations: "
        "(false, 'paper', 'paper') for paper mode OR "
        "(true, 'live', 'live') for live mode. "
        "No casual toggling allowed."
    )


def assert_mode_configuration_consistent() -> str:
    """Return the configured trading mode if env inputs form a valid state."""
    live_enabled, broker_mode, account_type = _get_env_mode_tuple()

    if not live_enabled and broker_mode == "paper" and account_type == "paper":
        return "paper"

    if live_enabled and broker_mode == "live" and account_type == "live":
        return "live"

    raise TradingControlMisconfiguredError(_misconfigured_message())


def get_trading_mode() -> TradingControlState:
    """Return the current mode-aware trading control state.

    The state is env-backed in MH-36B. We intentionally default valid paper
    mode to ``armed`` so existing manual paper submission behavior is preserved.
    """
    try:
        mode = assert_mode_configuration_consistent()
    except TradingControlMisconfiguredError as exc:
        settings = get_settings()
        configured_mode = settings.broker_mode.lower()
        if configured_mode not in {"paper", "live"}:
            configured_mode = "paper"
        return TradingControlState(
            trading_mode=configured_mode,
            execution_control="manual",
            arming_state="disarmed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=False,
            auto_trading_allowed=False,
            emergency_stop_active=False,
            reasons=(str(exc),),
        )

    if mode == "paper":
        return TradingControlState(
            trading_mode="paper",
            execution_control="manual",
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=False,
            emergency_stop_active=False,
            reasons=(),
        )

    return TradingControlState(
        trading_mode="live",
        execution_control="manual",
        arming_state="disarmed",
        live_order_submission_allowed=False,
        paper_order_submission_allowed=False,
        auto_trading_allowed=False,
        emergency_stop_active=False,
        reasons=(
            "live_order_submission_blocked_until_future_arming_risk_and_emergency_stop_gates",
        ),
    )


def assert_emergency_stop_clear() -> None:
    """Raise if trading is emergency-stopped.

    The env-backed MH-36B implementation never activates this state yet, but the
    guard exists now so later phases can wire it without changing submit paths.
    """
    state = get_trading_mode()
    if state.arming_state == "emergency_stopped" or state.emergency_stop_active:
        raise EmergencyStopActiveError("Trading is blocked by an active emergency stop.")


def assert_live_trading_armed() -> None:
    """Raise because live submission is not yet armed in MH-36B."""
    state = get_trading_mode()
    if state.trading_mode != "live":
        raise LiveTradingNotArmedError("Live trading is not the active trading mode.")
    raise LiveTradingNotArmedError(
        "Live order submission remains blocked until future live arming, risk, and emergency-stop gates are implemented."
    )


def assert_manual_trading_allowed(
    *,
    requested_mode: str | None = None,
    dry_run: bool = False,
) -> None:
    """Allow manual paper trading, allow live dry-run, block live submission."""
    current_mode = assert_mode_configuration_consistent()
    assert_emergency_stop_clear()
    mode = (requested_mode or current_mode).lower()

    if mode == "paper":
        return

    if mode == "live":
        if dry_run:
            return
        assert_live_trading_armed()
        return

    raise TradingControlError(f"Unsupported trading mode: {mode}")


def assert_auto_trading_allowed() -> None:
    """Block auto trading for both paper and live in MH-36B."""
    raise AutoTradingBlockedError(
        "Auto trading is not enabled in MH-36B. Manual trading only."
    )


_CONTROLLED_AUTO_PAPER_MAX_ORDERS_PER_RUN = 3
_CONTROLLED_AUTO_PAPER_MAX_ORDERS_PER_DAY = 25
_CONTROLLED_AUTO_PAPER_MAX_NOTIONAL_USD = 1000.0
_EQUITY_SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")
_AUTO_SUBMIT_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar(
    "auto_submit_context",
    default=None,
)


def _is_true_like(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_scheduled_worker_stack() -> bool:
    """Return True only for scheduler-driven auto-paper trader execution."""
    has_worker_frame = False
    has_scheduler_frame = False
    for frame in inspect.stack(context=0):
        filename = (frame.filename or "").replace("\\", "/")
        if filename.endswith("/auto_paper_trader_worker.py") and frame.function == "execute":
            has_worker_frame = True
        if "/apscheduler/" in filename:
            has_scheduler_frame = True
        if has_worker_frame and has_scheduler_frame:
            return True
    return False


def _is_kill_switch_inactive_if_available() -> bool:
    """Return False only when an active risk profile exists with kill-switch on."""
    try:
        from app.db.models.risk_profile import RiskProfile
        from app.db.session import SessionLocal
    except Exception:
        return True

    try:
        with SessionLocal() as session:
            profile = (
                session.query(RiskProfile)
                .filter(RiskProfile.is_active == "active")
                .first()
            )
    except Exception:
        return True

    if profile is None:
        return True
    return not bool(profile.kill_switch_enabled)


@contextmanager
def _controlled_auto_paper_submission_context(
    *,
    intent: str,
    ticker: str | None = None,
    order_type: str | None = None,
    quantity: Decimal | float | int | None = None,
    limit_price: Decimal | float | int | None = None,
    source: str | None = None,
    scheduled: bool | None = None,
):
    """Scope request metadata used by the controlled auto-paper gate.

    This keeps assert_order_submission_allowed(...) signature unchanged while
    allowing strict, contextual checks for scheduled auto-paper submits.
    """
    normalized_ticker = (ticker or "").strip().upper() or None
    normalized_order_type = (order_type or "").strip().upper() or None
    context = {
        "intent": (intent or "").strip().lower(),
        "ticker": normalized_ticker,
        "order_type": normalized_order_type,
        "quantity": float(quantity) if quantity is not None else None,
        "limit_price": float(limit_price) if limit_price is not None else None,
        "source": source,
        "scheduled": _is_scheduled_worker_stack() if scheduled is None else bool(scheduled),
    }
    token = _AUTO_SUBMIT_CONTEXT.set(context)
    try:
        yield
    finally:
        _AUTO_SUBMIT_CONTEXT.reset(token)


def is_controlled_auto_paper_allowed() -> bool:
    """Return True only if every env-level controlled auto-paper precondition holds.

    This is a narrow paper-only exception to the unconditional auto-trading
    block. It does NOT enable live, MARKET, multi-order, or non-TWS paths.
    The inner ``assert_auto_trading_allowed()`` remains unchanged and is still
    invoked on the non-controlled branch.
    """
    settings = get_settings()
    context = _AUTO_SUBMIT_CONTEXT.get()
    if not context:
        return False
    if context.get("intent") != "auto":
        return False
    if not bool(context.get("scheduled")):
        return False

    if not settings.auto_paper_enabled:
        return False
    if settings.live_execution_enabled:
        return False
    if settings.broker_mode.lower() != "paper":
        return False
    if settings.ibkr_account_type.lower() != "paper":
        return False
    if settings.broker_provider.lower() != "tws":
        return False
    if not settings.tws_enabled:
        return False
    if not settings.auto_paper_require_tws:
        return False
    if settings.auto_paper_order_type.upper() != "LIMIT":
        return False
    if settings.auto_paper_max_orders_per_run < 1:
        return False
    if settings.auto_paper_max_orders_per_run > _CONTROLLED_AUTO_PAPER_MAX_ORDERS_PER_RUN:
        return False
    if settings.auto_paper_max_orders_per_day < 1:
        return False
    if settings.auto_paper_max_orders_per_day > _CONTROLLED_AUTO_PAPER_MAX_ORDERS_PER_DAY:
        return False
    if settings.auto_paper_max_notional_usd <= 0:
        return False
    if settings.auto_paper_max_notional_usd > _CONTROLLED_AUTO_PAPER_MAX_NOTIONAL_USD:
        return False

    ticker = str(context.get("ticker") or "").upper()
    if not _EQUITY_SYMBOL_RE.fullmatch(ticker):
        return False

    allowlist_raw = settings.auto_paper_symbol_allowlist or ""
    allowlist = [s.strip().upper() for s in allowlist_raw.split(",") if s.strip()]
    if not allowlist:
        return False
    if ticker not in allowlist:
        return False

    request_order_type = str(context.get("order_type") or "").upper()
    if request_order_type != "LIMIT":
        return False

    if not _is_kill_switch_inactive_if_available():
        return False

    # PAPER_TRADING_ENABLED is not a Settings field; check env directly,
    # defaulting to True when the broker is already in paper mode.
    if not _is_true_like(os.getenv("PAPER_TRADING_ENABLED"), default=True):
        return False

    return True


def assert_order_submission_allowed(
    *,
    intent: str,
    requested_mode: str | None = None,
    dry_run: bool = False,
) -> None:
    """Validate whether an order path is allowed for the given intent."""
    normalized_intent = intent.lower()
    if normalized_intent == "auto":
        if is_controlled_auto_paper_allowed():
            assert_emergency_stop_clear()
            return
        assert_auto_trading_allowed()
        return
    if normalized_intent != "manual":
        raise TradingControlError(f"Unsupported execution intent: {intent}")
    assert_manual_trading_allowed(requested_mode=requested_mode, dry_run=dry_run)