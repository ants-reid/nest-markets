#!/usr/bin/env python3
"""Broker paper-trading pre-flight verification script.

Usage (from apps/api with venv activated):
    python scripts/verify_broker.py

Checks:
  1. Mode guard   — LIVE_EXECUTION_ENABLED, BROKER_MODE, IBKR_ACCOUNT_TYPE
  2. Account type — IBKR paper accounts have a DU prefix
  3. Gateway ping — lightweight probe to /iserver/auth/status

Exit codes:
  0 — all checks pass (paper_ready or paper_config_only)
  1 — misconfigured (live execution config detected)
  2 — unexpected error
"""
from __future__ import annotations

import asyncio
import sys

# Ensure the app package is importable when run from apps/api/
import os as _os
_HERE = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _green(s: str) -> str:
    return f"\033[92m{s}\033[0m"


def _red(s: str) -> str:
    return f"\033[91m{s}\033[0m"


def _yellow(s: str) -> str:
    return f"\033[93m{s}\033[0m"


def _bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


async def main() -> int:
    from app.config import get_settings
    from app.services.broker_mode_guard import (
        LiveExecutionBlockedError,
        assert_paper_mode,
        check_ibkr_gateway,
        is_paper_account_id,
    )

    settings = get_settings()

    print()
    print(_bold("═══════════════════════════════════════════════"))
    print(_bold("  Market Hunter — Broker Pre-Flight Verification"))
    print(_bold("═══════════════════════════════════════════════"))
    print()

    all_ok = True

    # ── Check 1: Mode guard ──────────────────────────────────────────
    print(_bold("1. Mode guard (broker_mode_guard.assert_paper_mode)"))
    try:
        assert_paper_mode()
        print(f"   BROKER_PROVIDER       : {settings.broker_provider}")
        print(f"   BROKER_MODE           : {settings.broker_mode}")
        print(f"   LIVE_EXECUTION_ENABLED: {settings.live_execution_enabled}")
        print(f"   IBKR_ACCOUNT_TYPE     : {settings.ibkr_account_type}")
        print(f"   Result: {_green('PASS')} — safe paper configuration")
    except LiveExecutionBlockedError as exc:
        print(f"   Result: {_red('FAIL')} — {exc}")
        all_ok = False
    print()

    # ── Check 2: Account ID prefix ───────────────────────────────────
    print(_bold("2. Account ID type (DU prefix = paper)"))
    account_id = settings.ibkr_account_id or ""
    if not account_id:
        print("   IBKR_ACCOUNT_ID: (not configured)")
        print(f"   Result: {_yellow('WARN')} — account ID not set; configure before connecting to gateway")
    elif is_paper_account_id(account_id):
        print(f"   IBKR_ACCOUNT_ID: {account_id}")
        print(f"   Result: {_green('PASS')} — DU prefix confirms paper account")
    else:
        print(f"   IBKR_ACCOUNT_ID: {account_id}")
        print(f"   Result: {_red('FAIL')} — account ID does not have DU prefix; looks like a live account")
        all_ok = False
    print()

    # ── Check 3: Gateway reachability ───────────────────────────────
    print(_bold("3. IBKR gateway reachability (GET /iserver/auth/status)"))
    print(f"   Gateway URL: {settings.ibkr_gateway_url}")
    print("   Probing... ", end="", flush=True)
    reachable = await check_ibkr_gateway(settings.ibkr_gateway_url, timeout=5.0)
    if reachable:
        print(f"{_green('REACHABLE')}")
        print(f"   Result: {_green('PASS')} — gateway responded")
    else:
        print(f"{_yellow('UNREACHABLE')}")
        print(f"   Result: {_yellow('WARN')} — gateway not responding (not yet started?)")
        print("             Paper trading config is correct; start the IBKR gateway to proceed")
    print()

    # ── Summary ──────────────────────────────────────────────────────
    print(_bold("═══════════════════════════════════════════════"))
    if not all_ok:
        print(_red(_bold("  VERDICT: MISCONFIGURED — live execution config detected!")))
        print(_red("  Fix LIVE_EXECUTION_ENABLED, BROKER_MODE, or IBKR_ACCOUNT_TYPE"))
        print(_bold("═══════════════════════════════════════════════"))
        print()
        return 1
    elif reachable:
        print(_green(_bold("  VERDICT: PAPER_READY — all checks passed")))
        print(_bold("═══════════════════════════════════════════════"))
        print()
        return 0
    else:
        print(_yellow(_bold("  VERDICT: PAPER_CONFIG_ONLY — config is safe, gateway not running")))
        print(_bold("═══════════════════════════════════════════════"))
        print()
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as exc:
        print(f"\033[91mERROR: {exc}\033[0m", file=sys.stderr)
        sys.exit(2)
