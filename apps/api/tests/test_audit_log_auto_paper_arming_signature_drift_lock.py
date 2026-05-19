"""MH-DRIFTLOCK-AUDIT-LOG-AUTO-PAPER-ARMING-SIGNATURE-PIN

Pins the parameter list & defaults of ``audit_log_service.log_auto_paper_arming_action``.
This is the durable trail for the auto-paper arming state machine; widening
it silently could let arming events drop fields without detection.
"""
from __future__ import annotations

import inspect

from app.services import audit_log_service

_REQUIRED_PARAMS: tuple[str, ...] = ("action", "requested_by", "reason", "result_status")
_OPTIONAL_PARAMS_WITH_DEFAULTS: dict[str, object] = {
    "client_request_id": None,
    "failure_reasons": None,
    "warning_codes": None,
    "enablement_checked_at": None,
    "enablement_status": None,
    "enablement_blockers": None,
    "enablement_warnings": None,
    "trading_mode": None,
    "execution_control": None,
    "arming_state_before": None,
    "arming_state_after": None,
    "extra": None,
}


def test_log_auto_paper_arming_required_parameters() -> None:
    sig = inspect.signature(audit_log_service.log_auto_paper_arming_action)
    names = [p.name for p in sig.parameters.values()]
    for req in _REQUIRED_PARAMS:
        assert req in names, f"log_auto_paper_arming_action missing required param: {req}"


def test_log_auto_paper_arming_optional_defaults() -> None:
    sig = inspect.signature(audit_log_service.log_auto_paper_arming_action)
    for name, expected in _OPTIONAL_PARAMS_WITH_DEFAULTS.items():
        assert name in sig.parameters, (
            f"log_auto_paper_arming_action missing optional param: {name}"
        )
        assert sig.parameters[name].default == expected, (
            f"log_auto_paper_arming_action.{name} default drift: expected {expected!r}, "
            f"got {sig.parameters[name].default!r}"
        )


def test_log_auto_paper_arming_parameter_count_pin() -> None:
    sig = inspect.signature(audit_log_service.log_auto_paper_arming_action)
    expected = len(_REQUIRED_PARAMS) + len(_OPTIONAL_PARAMS_WITH_DEFAULTS)
    assert len(sig.parameters) == expected, (
        f"log_auto_paper_arming_action parameter count drift: expected {expected}, "
        f"got {len(sig.parameters)}. Params: {list(sig.parameters)!r}"
    )
