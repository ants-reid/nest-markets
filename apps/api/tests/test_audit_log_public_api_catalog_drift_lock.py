"""MH-DRIFTLOCK-AUDIT-LOG-PUBLIC-API-CATALOG

Pins the public ``log_*`` functions exported by ``audit_log_service``. These
are the durable-trail entry points; any silent rename or removal breaks the
audit contract.
"""
from __future__ import annotations

from app.services import audit_log_service

_EXPECTED_LOG_FUNCTIONS: frozenset[str] = frozenset(
    {
        "log_approval_action",
        "log_auto_paper_arming_action",
        "log_broker_order_event",
        "log_trade_submitted",
        "log_workflow_run",
    }
)


def _exported_log_functions() -> frozenset[str]:
    return frozenset(
        n for n in dir(audit_log_service)
        if n.startswith("log_") and callable(getattr(audit_log_service, n))
    )


def test_audit_log_public_api_exact_catalog() -> None:
    actual = _exported_log_functions()
    missing = _EXPECTED_LOG_FUNCTIONS - actual
    extra = actual - _EXPECTED_LOG_FUNCTIONS
    assert not missing, f"audit_log_service missing required exports: {sorted(missing)}"
    assert not extra, (
        f"audit_log_service has new public log_* exports: {sorted(extra)} — "
        "update _EXPECTED_LOG_FUNCTIONS under an explicit drift-lock cycle."
    )


def test_audit_log_function_floor() -> None:
    assert len(_exported_log_functions()) >= len(_EXPECTED_LOG_FUNCTIONS)
