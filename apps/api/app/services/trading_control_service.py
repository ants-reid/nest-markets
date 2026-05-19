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

from dataclasses import dataclass

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


def assert_order_submission_allowed(
    *,
    intent: str,
    requested_mode: str | None = None,
    dry_run: bool = False,
) -> None:
    """Validate whether an order path is allowed for the given intent."""
    normalized_intent = intent.lower()
    if normalized_intent == "auto":
        assert_auto_trading_allowed()
        return
    if normalized_intent != "manual":
        raise TradingControlError(f"Unsupported execution intent: {intent}")
    assert_manual_trading_allowed(requested_mode=requested_mode, dry_run=dry_run)