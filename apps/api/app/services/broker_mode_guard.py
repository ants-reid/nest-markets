"""Broker mode guard — enforce mode consistency for paper or live execution.

MH-36 rule (supports both modes):
  - IBKR data access              → always allowed
  - IBKR paper account execution  → allowed when LIVE_EXECUTION_ENABLED=false, BROKER_MODE=paper, IBKR_ACCOUNT_TYPE=paper
  - IBKR live account execution   → allowed only when ALL three are set to live values:
                                     LIVE_EXECUTION_ENABLED=true, BROKER_MODE=live, IBKR_ACCOUNT_TYPE=live
  - Any mismatched config         → blocked; raises BrokerModeInconsistencyError

No casual toggling between paper/live. All three must match, or execution is rejected.
"""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.services.trading_control_service import assert_mode_configuration_consistent
from app.services.trading_control_service import TradingControlMisconfiguredError

_logger = logging.getLogger(__name__)

# IBKR paper accounts have a "DU" prefix (Demo Unified); live accounts start with "U".
_PAPER_ACCOUNT_PREFIXES = ("DU",)


class LiveExecutionBlockedError(Exception):
    """Raised when broker mode is misconfigured or inconsistent.
    
    In MH-36, this error is raised when:
    - Mode is neither all-paper nor all-live (mismatched config)
    - Paper mode requires: LIVE_EXECUTION_ENABLED=false, BROKER_MODE=paper, IBKR_ACCOUNT_TYPE=paper
    - Live mode requires: LIVE_EXECUTION_ENABLED=true, BROKER_MODE=live, IBKR_ACCOUNT_TYPE=live
    """


# Alias for clarity; both names refer to the same error
BrokerModeInconsistencyError = LiveExecutionBlockedError


def assert_paper_mode() -> None:
    """Deprecated compatibility shim for the legacy paper-named guard.

    MH-36B moves order gating to the mode-aware trading control service. This
    function stays in place only for tests and backward compatibility and now
    validates env consistency only.
    """
    try:
        mode = assert_mode_configuration_consistent()
    except TradingControlMisconfiguredError as exc:
        raise BrokerModeInconsistencyError(str(exc)) from exc

    if mode == "paper":
        _logger.debug("broker_mode_guard: paper mode config confirmed")
    else:
        _logger.debug("broker_mode_guard: live mode config confirmed")


def get_broker_mode_metadata() -> dict[str, object]:
    """Return current broker mode metadata for embedding in API responses.

    Returns:
        {
            "broker": "ibkr",
            "mode": "paper" or "live",
            "live_execution_enabled": bool,
            "paper_trading_enabled": bool,
        }
    """
    settings = get_settings()
    live_enabled = settings.live_execution_enabled
    broker_mode = settings.broker_mode.lower()
    account_type = settings.ibkr_account_type.lower()

    # Determine if we're in a valid paper mode
    is_valid_paper = (
        not live_enabled
        and broker_mode == "paper"
        and account_type == "paper"
    )

    # Determine if we're in a valid live mode
    is_valid_live = (
        live_enabled
        and broker_mode == "live"
        and account_type == "live"
    )

    # Report actual mode if valid; otherwise use broker_mode as-is for diagnostics
    actual_mode = "live" if is_valid_live else broker_mode

    return {
        "broker": settings.broker_provider,
        "mode": actual_mode,
        "live_execution_enabled": live_enabled,
        "paper_trading_enabled": is_valid_paper,
    }


def is_live_mode_enabled() -> bool:
    """Return True if live mode is properly configured and enabled.

    Returns:
        True only if LIVE_EXECUTION_ENABLED=true AND BROKER_MODE=live AND IBKR_ACCOUNT_TYPE=live.
        False otherwise (including misconfigured states).
    """
    settings = get_settings()
    return (
        settings.live_execution_enabled
        and settings.broker_mode.lower() == "live"
        and settings.ibkr_account_type.lower() == "live"
    )


async def check_ibkr_gateway(gateway_url: str, timeout: float = 5.0) -> bool:
    """Probe the IBKR Client Portal Gateway to test reachability.

    Calls ``GET /iserver/auth/status`` — a lightweight read-only endpoint that
    returns the session's authenticated state without triggering any orders.

    Args:
        gateway_url: Base gateway URL (e.g. ``https://localhost:5001/v1/api``).
        timeout:     HTTP timeout in seconds (default 5 s — short for health probes).

    Returns:
        True if the gateway responds with any non-5xx status; False otherwise.
    """
    try:
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            resp = await client.get(f"{gateway_url}/iserver/auth/status")
            return resp.status_code < 500
    except Exception as exc:  # noqa: BLE001
        _logger.debug("IBKR gateway probe failed: %s", exc)
        return False


def is_paper_account_id(account_id: str) -> bool:
    """Return True if account_id looks like an IBKR paper account.

    IBKR paper (Demo Unified) account IDs begin with "DU".
    An empty/unconfigured ID is treated as paper-safe (not yet provisioned).

    Args:
        account_id: IBKR account ID string (e.g. "DUP153837").

    Returns:
        True for DU-prefixed IDs and empty/unconfigured IDs.
        False for live account IDs (e.g. "U1234567").
    """
    if not account_id:
        return True  # not yet configured — treat as safe
    return any(account_id.upper().startswith(pfx) for pfx in _PAPER_ACCOUNT_PREFIXES)
