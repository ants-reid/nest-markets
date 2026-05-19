"""MH-DRIFTLOCK-AUDIT-LOG-APPROVAL-ACTION-SIGNATURE-PIN

Pins the parameter list & defaults of ``audit_log_service.log_approval_action``.
"""
from __future__ import annotations

import inspect

from app.services import audit_log_service

_REQUIRED_PARAMS: tuple[str, ...] = ("approval_id", "action")
_OPTIONAL_PARAMS_WITH_DEFAULTS: dict[str, object] = {"asset": None, "extra": None}


def test_log_approval_action_required_parameters() -> None:
    sig = inspect.signature(audit_log_service.log_approval_action)
    names = [p.name for p in sig.parameters.values()]
    for req in _REQUIRED_PARAMS:
        assert req in names, f"log_approval_action missing required param: {req}"


def test_log_approval_action_optional_defaults() -> None:
    sig = inspect.signature(audit_log_service.log_approval_action)
    for name, expected in _OPTIONAL_PARAMS_WITH_DEFAULTS.items():
        assert name in sig.parameters, f"log_approval_action missing optional param: {name}"
        assert sig.parameters[name].default == expected, (
            f"log_approval_action.{name} default drift: expected {expected!r}, "
            f"got {sig.parameters[name].default!r}"
        )


def test_log_approval_action_parameter_count_pin() -> None:
    sig = inspect.signature(audit_log_service.log_approval_action)
    expected = len(_REQUIRED_PARAMS) + len(_OPTIONAL_PARAMS_WITH_DEFAULTS)
    assert len(sig.parameters) == expected, (
        f"log_approval_action parameter count drift: expected {expected}, "
        f"got {len(sig.parameters)}. Params: {list(sig.parameters)!r}"
    )
