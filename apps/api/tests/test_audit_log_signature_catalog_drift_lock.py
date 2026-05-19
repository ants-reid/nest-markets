"""Drift-lock: audit_log_service safety-function signature catalog (cycle 68).

Pins the keyword-argument names of the three safety audit functions.
A silent rename of ``idempotency_key`` -> ``key`` would break audit
attribution on every trade-submit row written from that point on
without raising any test outside this one.

Test-only / additive.
"""

from __future__ import annotations

import inspect

from app.services import audit_log_service

EXPECTED_SIGNATURES: dict[str, tuple[str, ...]] = {
    "log_trade_submitted": (
        "endpoint",
        "asset",
        "side",
        "qty",
        "notional",
        "idempotency_key",
        "extra",
    ),
    "log_workflow_run": (
        "asset",
        "timeframe",
        "execution_mode",
        "outcome",
        "idempotency_key",
        "extra",
    ),
    "log_broker_order_event": (
        "action",
        "ticker",
        "side",
        "quantity",
        "status",
        "broker_order_id",
        "reason",
        "dry_run",
        "issues",
        "extra",
    ),
}


def test_safety_audit_function_signatures_unchanged() -> None:
    drift: list[str] = []
    for fname, expected_params in EXPECTED_SIGNATURES.items():
        fn = getattr(audit_log_service, fname)
        actual_params = tuple(inspect.signature(fn).parameters.keys())
        if actual_params != expected_params:
            drift.append(
                f"  {fname}: expected {expected_params}, got {actual_params}"
            )
    assert not drift, (
        "Safety audit-function signature drift detected. Renaming a "
        "kwarg silently breaks every caller relying on the old name "
        "and produces audit rows with NULL columns.\n"
        + "\n".join(drift)
    )


def test_idempotency_key_kwarg_present_on_safety_audits() -> None:
    """Hard guard: the two functions that record trade-submit / workflow-run
    MUST accept ``idempotency_key`` so audit rows can be correlated back
    to the originating client request.
    """
    for fname in ("log_trade_submitted", "log_workflow_run"):
        fn = getattr(audit_log_service, fname)
        params = inspect.signature(fn).parameters
        assert "idempotency_key" in params, (
            f"{fname} no longer accepts idempotency_key — audit rows "
            "for trade submissions can no longer be correlated to the "
            "client's idempotency token."
        )
