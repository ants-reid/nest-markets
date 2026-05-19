"""MH-DRIFTLOCK-AUDIT-LOG-BROKER-ORDER-EVENT-SIGNATURE-PIN

Pins the parameter list & defaults of ``audit_log_service.log_broker_order_event``.
``dry_run`` defaults to False — silent flip would conceal real submissions
in the audit trail; this test makes that loud.
"""
from __future__ import annotations

import inspect

from app.services import audit_log_service

_REQUIRED_PARAMS: tuple[str, ...] = ("action", "ticker", "side", "quantity", "status")
_OPTIONAL_PARAMS_WITH_DEFAULTS: dict[str, object] = {
    "broker_order_id": None,
    "reason": None,
    "dry_run": False,
    "issues": None,
    "extra": None,
}


def test_log_broker_order_event_required_parameters() -> None:
    sig = inspect.signature(audit_log_service.log_broker_order_event)
    names = [p.name for p in sig.parameters.values()]
    for req in _REQUIRED_PARAMS:
        assert req in names, f"log_broker_order_event missing required param: {req}"


def test_log_broker_order_event_optional_defaults() -> None:
    sig = inspect.signature(audit_log_service.log_broker_order_event)
    for name, expected in _OPTIONAL_PARAMS_WITH_DEFAULTS.items():
        assert name in sig.parameters, (
            f"log_broker_order_event missing optional param: {name}"
        )
        assert sig.parameters[name].default == expected, (
            f"log_broker_order_event.{name} default drift: expected {expected!r}, "
            f"got {sig.parameters[name].default!r}"
        )


def test_log_broker_order_event_dry_run_default_false() -> None:
    sig = inspect.signature(audit_log_service.log_broker_order_event)
    assert sig.parameters["dry_run"].default is False, (
        "log_broker_order_event.dry_run must default to False — silently "
        "defaulting to True would mark live submissions as dry_run in the trail."
    )


def test_log_broker_order_event_parameter_count_pin() -> None:
    sig = inspect.signature(audit_log_service.log_broker_order_event)
    expected = len(_REQUIRED_PARAMS) + len(_OPTIONAL_PARAMS_WITH_DEFAULTS)
    assert len(sig.parameters) == expected, (
        f"log_broker_order_event parameter count drift: expected {expected}, "
        f"got {len(sig.parameters)}. Params: {list(sig.parameters)!r}"
    )
