"""Drift-lock: audit_log_service method catalog (cycle 67).

Pins the set of ``log_*`` functions exported by
``app.services.audit_log_service``. Removing any of these silently
drops an audit trail; renaming silently breaks every caller; adding a
new one triggers an explicit ledger update.

Test-only / additive.
"""

from __future__ import annotations

import inspect

from app.services import audit_log_service

EXPECTED_LOG_FUNCTIONS: frozenset[str] = frozenset(
    {
        "log_trade_submitted",
        "log_approval_action",
        "log_workflow_run",
        "log_broker_order_event",
        "log_auto_paper_arming_action",
    }
)

SAFETY_REQUIRED_LOG_FUNCTIONS: frozenset[str] = frozenset(
    {
        "log_trade_submitted",
        "log_workflow_run",
        "log_broker_order_event",
    }
)


def _log_functions() -> set[str]:
    return {
        name
        for name, fn in inspect.getmembers(audit_log_service, inspect.isfunction)
        if name.startswith("log_") and fn.__module__ == audit_log_service.__name__
    }


def test_audit_log_function_catalog_exact_match() -> None:
    actual = _log_functions()
    extra = actual - EXPECTED_LOG_FUNCTIONS
    missing = EXPECTED_LOG_FUNCTIONS - actual
    msg: list[str] = []
    if extra:
        msg.append("  Unexpected new audit_log_service.log_* function(s): "
                   + ", ".join(sorted(extra)))
    if missing:
        msg.append("  Missing expected audit_log_service.log_* function(s): "
                   + ", ".join(sorted(missing)))
    assert not msg, (
        "audit_log_service log_* function catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, update EXPECTED_LOG_FUNCTIONS and ensure "
        "every caller of any removed/renamed function is migrated."
    )


def test_safety_log_functions_present() -> None:
    actual = _log_functions()
    missing = SAFETY_REQUIRED_LOG_FUNCTIONS - actual
    assert not missing, (
        "SAFETY-required audit functions missing: "
        f"{sorted(missing)}. Removing these would silently drop the "
        "trade-submit / workflow-run / broker-order audit trail."
    )


def test_safety_subset_within_full_catalog() -> None:
    assert SAFETY_REQUIRED_LOG_FUNCTIONS <= EXPECTED_LOG_FUNCTIONS, (
        "SAFETY_REQUIRED_LOG_FUNCTIONS is not a subset of "
        "EXPECTED_LOG_FUNCTIONS — catalogs out of sync."
    )
