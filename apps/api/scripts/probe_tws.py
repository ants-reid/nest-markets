"""Standalone read-only TWS / IB Gateway probe.

This script is intentionally NOT wired into the application. It only verifies
that the TWS or IB Gateway socket API is reachable in paper mode and that the
expected account is visible. It never calls placeOrder / cancelOrder.
"""

from __future__ import annotations

import os
import sys
from typing import Any

try:
    from ib_async import IB
except Exception as exc:  # pragma: no cover - import guard
    print(f"FATAL: ib_async not importable: {type(exc).__name__}: {exc}")
    sys.exit(2)


HOST = os.environ.get("IBKR_TWS_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBKR_TWS_PORT", "4002"))
CLIENT_ID = int(os.environ.get("IBKR_TWS_CLIENT_ID", "42"))
EXPECTED_ACCOUNT = os.environ.get("IBKR_ACCOUNT_ID", "DUP153837")

SUMMARY_TAGS = ["NetLiquidation", "AvailableFunds", "BuyingPower"]


def _mask(value: str) -> str:
    if not value or len(value) <= 4:
        return "***"
    return value[:2] + "***" + value[-2:]


async def run() -> int:
    ib = IB()
    print(f"Connecting host={HOST} port={PORT} client_id={CLIENT_ID} ...")
    try:
        await ib.connectAsync(
            HOST,
            PORT,
            clientId=CLIENT_ID,
            readonly=True,
            timeout=15,
        )
    except Exception as exc:
        print(f"FAIL: connect error: {type(exc).__name__}: {exc}")
        return 1

    exit_code = 0
    try:
        print(f"OK: connected={ib.isConnected()}")
        accounts = list(ib.managedAccounts() or [])
        print(f"managed_accounts={accounts}")
        present = EXPECTED_ACCOUNT in accounts
        print(f"expected_account={_mask(EXPECTED_ACCOUNT)} present={present}")
        if not present:
            exit_code = 3

        target = EXPECTED_ACCOUNT if present else (accounts[0] if accounts else "")
        if target:
            try:
                rows: list[Any] = await ib.accountSummaryAsync(target)
            except Exception as exc:
                rows = []
                print(f"WARN: accountSummary error: {type(exc).__name__}: {exc}")
            wanted = {tag: None for tag in SUMMARY_TAGS}
            currency: str | None = None
            for r in rows:
                tag = getattr(r, "tag", None)
                if tag in wanted and wanted[tag] is None:
                    wanted[tag] = getattr(r, "value", None)
                    currency = currency or getattr(r, "currency", None)
            for tag in SUMMARY_TAGS:
                print(f"summary.{tag}={wanted[tag]}")
            print(f"summary.Currency={currency}")

            try:
                positions = ib.positions(target)
            except Exception as exc:
                positions = []
                print(f"WARN: positions error: {type(exc).__name__}: {exc}")
            print(f"positions_count={len(positions)}")
            for p in positions[:5]:
                con = getattr(p, "contract", None)
                sym = getattr(con, "symbol", "?") if con else "?"
                sec = getattr(con, "secType", "?") if con else "?"
                qty = getattr(p, "position", "?")
                avg = getattr(p, "avgCost", "?")
                print(f"  position symbol={sym} secType={sec} qty={qty} avgCost={avg}")
        else:
            print("WARN: no managed accounts returned; skipping summary/positions")
            exit_code = exit_code or 4
    finally:
        try:
            ib.disconnect()
            print("disconnected")
        except Exception as exc:
            print(f"WARN: disconnect error: {type(exc).__name__}: {exc}")

    return exit_code


def main() -> int:
    ib = IB()
    print(f"Connecting host={HOST} port={PORT} client_id={CLIENT_ID} ...")
    try:
        ib.connect(HOST, PORT, clientId=CLIENT_ID, readonly=True, timeout=15)
    except Exception as exc:
        print(f"FAIL: connect error: {type(exc).__name__}: {exc}")
        return 1

    exit_code = 0
    try:
        print(f"OK: connected={ib.isConnected()}")
        accounts = list(ib.managedAccounts() or [])
        print(f"managed_accounts={accounts}")
        present = EXPECTED_ACCOUNT in accounts
        print(f"expected_account={_mask(EXPECTED_ACCOUNT)} present={present}")
        if not present:
            exit_code = 3

        target = EXPECTED_ACCOUNT if present else (accounts[0] if accounts else "")
        if target:
            try:
                rows: list[Any] = ib.accountSummary(target)
            except Exception as exc:
                rows = []
                print(f"WARN: accountSummary error: {type(exc).__name__}: {exc}")
            wanted: dict[str, Any] = {tag: None for tag in SUMMARY_TAGS}
            currency: str | None = None
            for r in rows:
                tag = getattr(r, "tag", None)
                if tag in wanted and wanted[tag] is None:
                    wanted[tag] = getattr(r, "value", None)
                    currency = currency or getattr(r, "currency", None)
            for tag in SUMMARY_TAGS:
                print(f"summary.{tag}={wanted[tag]}")
            print(f"summary.Currency={currency}")

            try:
                positions = ib.positions(target)
            except Exception as exc:
                positions = []
                print(f"WARN: positions error: {type(exc).__name__}: {exc}")
            print(f"positions_count={len(positions)}")
            for p in positions[:5]:
                con = getattr(p, "contract", None)
                sym = getattr(con, "symbol", "?") if con else "?"
                sec = getattr(con, "secType", "?") if con else "?"
                qty = getattr(p, "position", "?")
                avg = getattr(p, "avgCost", "?")
                print(f"  position symbol={sym} secType={sec} qty={qty} avgCost={avg}")
        else:
            print("WARN: no managed accounts returned; skipping summary/positions")
            exit_code = exit_code or 4
    finally:
        try:
            ib.disconnect()
            print("disconnected")
        except Exception as exc:
            print(f"WARN: disconnect error: {type(exc).__name__}: {exc}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
