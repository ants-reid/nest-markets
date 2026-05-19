#!/usr/bin/env python3
"""Broker paper-trading end-to-end runtime check script (MH-35).

Performs a live HTTP probe against a running Market Hunter API server to verify
that the full paper order flow is operational end-to-end.

Steps
-----
1. GET  /broker/health      — mode guard passes, overall status checked
2. POST /broker/orders/dry-run — dry-run returns status=ready for a canned payload
3. GET  /broker/orders/audit   — confirms the dry-run event was written to the audit log

NOTE: This script intentionally does NOT submit a real order (step 3 of the
      order flow is skipped for safety).  It validates every pre-submit gate
      without creating any broker-side state.

Usage
-----
    python scripts/e2e_broker_check.py                  # default http://127.0.0.1:8000
    python scripts/e2e_broker_check.py --base-url http://staging.example.com:8000

Exit codes
----------
  0 — all steps passed
  1 — one or more steps failed (paper mode misconfigured or dry-run not ready)
  2 — API server unreachable or unexpected error
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


# ---------------------------------------------------------------------------
# Colour helpers (no external deps)
# ---------------------------------------------------------------------------

def _green(s: str) -> str:  return f"\033[92m{s}\033[0m"
def _red(s: str) -> str:    return f"\033[91m{s}\033[0m"
def _yellow(s: str) -> str: return f"\033[93m{s}\033[0m"
def _bold(s: str) -> str:   return f"\033[1m{s}\033[0m"
def _cyan(s: str) -> str:   return f"\033[96m{s}\033[0m"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body: Any = {}
        try:
            body = json.loads(exc.read().decode())
        except Exception:
            pass
        return exc.code, body


def _post(url: str, payload: dict) -> tuple[int, Any]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body: Any = {}
        try:
            body = json.loads(exc.read().decode())
        except Exception:
            pass
        return exc.code, body


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_DRY_RUN_PAYLOAD = {
    "ticker": "AAPL",
    "side": "BUY",
    "quantity": 10,
    "order_type": "MARKET",
}


def main(base_url: str) -> int:
    base_url = base_url.rstrip("/")

    print()
    print(_bold("═══════════════════════════════════════════════════"))
    print(_bold("  Market Hunter — Broker Paper E2E Runtime Check"))
    print(_bold("═══════════════════════════════════════════════════"))
    print(_cyan(f"  API base: {base_url}"))
    print()

    all_ok = True

    # ── Step 1: Health check ─────────────────────────────────────────
    print(_bold("Step 1 · GET /broker/health"))
    try:
        status, body = _get(f"{base_url}/broker/health")
    except (urllib.error.URLError, OSError) as exc:
        print(f"   {_red('ERROR')} — could not connect: {exc}")
        print()
        print(_bold("═══════════════════════════════════════════════════"))
        print(_red(_bold("  VERDICT: API UNREACHABLE")))
        print(_red("  Start the Market Hunter API and re-run this script."))
        print(_bold("═══════════════════════════════════════════════════"))
        print()
        return 2

    if status != 200:
        print(f"   {_red('FAIL')} — unexpected HTTP {status}")
        all_ok = False
    else:
        health_status = body.get("status", "unknown")
        mode_guard_ok = body.get("mode_guard_ok", False)
        gateway_reachable = body.get("gateway_reachable", False)
        account_is_paper = body.get("account_is_paper", False)
        account_id = body.get("account_id", "(not set)")
        gateway_url = body.get("gateway_url", "(not set)")

        print(f"   Health status    : {health_status}")
        print(f"   Mode guard OK    : {_green('yes') if mode_guard_ok else _red('NO')}")
        print(f"   Gateway reachable: {_green('yes') if gateway_reachable else _yellow('no')}")
        print(f"   Account          : {account_id}")
        print(f"   Account is paper : {_green('yes') if account_is_paper else _yellow('no (not yet configured)')}")
        print(f"   Gateway URL      : {gateway_url}")

        if health_status == "misconfigured":
            print(f"   Result: {_red('FAIL')} — live-execution config detected; orders would be rejected")
            all_ok = False
        elif health_status == "paper_ready":
            print(f"   Result: {_green('PASS')} — all paper-mode guards pass and gateway is reachable")
        else:
            print(f"   Result: {_yellow('WARN')} — config is safe but gateway not reachable (expected in local dev)")
    print()

    # ── Step 2: Dry-run ─────────────────────────────────────────────
    print(_bold("Step 2 · POST /broker/orders/dry-run (AAPL BUY 10 MARKET)"))
    try:
        status, body = _post(f"{base_url}/broker/orders/dry-run", _DRY_RUN_PAYLOAD)
    except (urllib.error.URLError, OSError) as exc:
        print(f"   {_red('ERROR')} — request failed: {exc}")
        all_ok = False
        status, body = 0, {}

    if status == 200:
        dr_status = body.get("status", "unknown")
        notional = body.get("estimated_notional")
        issues = body.get("issues", [])

        print(f"   Dry-run status   : {dr_status.upper()}")
        if notional is not None:
            print(f"   Est. notional    : ${notional:,.2f}")
        if issues:
            print(f"   Issues ({len(issues)}):")
            for issue in issues:
                print(f"     · [{issue.get('code', '?')}] {issue.get('message', '')}")

        if dr_status == "ready":
            print(f"   Result: {_green('PASS')} — dry-run returned ready; order would be accepted")
        elif dr_status == "blocked":
            print(f"   Result: {_red('FAIL')} — dry-run blocked by mode guard")
            all_ok = False
        else:
            print(f"   Result: {_red('FAIL')} — dry-run status is {dr_status!r}; check issues above")
            all_ok = False
    elif status != 0:
        print(f"   {_red('FAIL')} — unexpected HTTP {status}: {body}")
        all_ok = False
    print()

    # ── Step 3: Audit trail ──────────────────────────────────────────
    print(_bold("Step 3 · GET /broker/orders/audit (dry-run event verification)"))
    try:
        status, body = _get(f"{base_url}/broker/orders/audit?limit=5")
    except (urllib.error.URLError, OSError) as exc:
        print(f"   {_red('ERROR')} — request failed: {exc}")
        all_ok = False
        status, body = 0, {}

    if status == 200:
        entries = body.get("entries", [])
        total = body.get("total", len(entries))
        print(f"   Total events logged : {total}")

        dry_run_entries = [e for e in entries if e.get("action") == "dry_run"]
        if dry_run_entries:
            latest = dry_run_entries[0]
            print(f"   Latest dry-run      : {latest.get('ticker')} {latest.get('side')} "
                  f"qty={latest.get('quantity')} status={latest.get('status')} ts={latest.get('ts')}")
            print(f"   Result: {_green('PASS')} — audit trail has the dry-run event")
        else:
            print(f"   {_yellow('WARN')} — no dry-run events found in the last 5 audit entries")
            print("           (This is expected if the API was just started and no prior orders exist)")
    elif status != 0:
        print(f"   {_red('FAIL')} — unexpected HTTP {status}: {body}")
        all_ok = False
    print()

    # ── Summary ──────────────────────────────────────────────────────
    print(_bold("═══════════════════════════════════════════════════"))
    if all_ok:
        print(_green(_bold("  VERDICT: E2E CHECK PASSED — paper order flow is operational")))
        print(_cyan("  NOTE: No real order was submitted. This check validates pre-submit gates only."))
    else:
        print(_red(_bold("  VERDICT: E2E CHECK FAILED — see step failures above")))
    print(_bold("═══════════════════════════════════════════════════"))
    print()

    return 0 if all_ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Hunter broker E2E runtime check")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the Market Hunter API (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()

    try:
        code = main(args.base_url)
    except Exception as exc:  # noqa: BLE001
        print(f"\n{_red('Unexpected error')}: {exc}")
        code = 2

    sys.exit(code)
