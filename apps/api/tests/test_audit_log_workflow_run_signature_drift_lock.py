"""MH-DRIFTLOCK-AUDIT-LOG-WORKFLOW-RUN-SIGNATURE-PIN

Pins the parameter list & defaults of ``audit_log_service.log_workflow_run``.
Adding a positional parameter or removing a required one would silently
break the workflow audit trail.
"""
from __future__ import annotations

import inspect

from app.services import audit_log_service

_REQUIRED_PARAMS: tuple[str, ...] = ("asset", "timeframe", "execution_mode", "outcome")
_OPTIONAL_PARAMS_WITH_DEFAULTS: dict[str, object] = {
    "idempotency_key": None,
    "extra": None,
}


def test_log_workflow_run_required_parameters() -> None:
    sig = inspect.signature(audit_log_service.log_workflow_run)
    names = [p.name for p in sig.parameters.values()]
    for req in _REQUIRED_PARAMS:
        assert req in names, f"log_workflow_run missing required param: {req}"


def test_log_workflow_run_optional_defaults() -> None:
    sig = inspect.signature(audit_log_service.log_workflow_run)
    for name, expected in _OPTIONAL_PARAMS_WITH_DEFAULTS.items():
        assert name in sig.parameters, f"log_workflow_run missing optional param: {name}"
        assert sig.parameters[name].default == expected, (
            f"log_workflow_run.{name} default drift: expected {expected!r}, "
            f"got {sig.parameters[name].default!r}"
        )


def test_log_workflow_run_parameter_count_pin() -> None:
    sig = inspect.signature(audit_log_service.log_workflow_run)
    expected = len(_REQUIRED_PARAMS) + len(_OPTIONAL_PARAMS_WITH_DEFAULTS)
    actual = len(sig.parameters)
    assert actual == expected, (
        f"log_workflow_run parameter count drift: expected {expected}, got {actual}. "
        f"Params: {list(sig.parameters)!r}"
    )
