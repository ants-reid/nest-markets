"""MH-DRIFTLOCK-AUDIT-LOG-TRADE-SUBMITTED-SIGNATURE-PIN

Pins the parameter list & defaults of ``audit_log_service.log_trade_submitted``.
Adding a parameter (especially a positional one) could let callers smuggle
data past the durable trail; removing one would break call sites silently.
"""
from __future__ import annotations

import inspect

from app.services import audit_log_service

_REQUIRED_PARAMS: tuple[str, ...] = ("endpoint", "asset", "side", "qty", "notional")
_OPTIONAL_PARAMS_WITH_DEFAULTS: dict[str, object] = {
    "idempotency_key": None,
    "extra": None,
}


def test_log_trade_submitted_required_parameters() -> None:
    sig = inspect.signature(audit_log_service.log_trade_submitted)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    for req in _REQUIRED_PARAMS:
        assert req in names, f"log_trade_submitted missing required param: {req}"


def test_log_trade_submitted_optional_defaults() -> None:
    sig = inspect.signature(audit_log_service.log_trade_submitted)
    for name, expected in _OPTIONAL_PARAMS_WITH_DEFAULTS.items():
        assert name in sig.parameters, f"log_trade_submitted missing optional param: {name}"
        assert sig.parameters[name].default == expected, (
            f"log_trade_submitted.{name} default drift: expected {expected!r}, "
            f"got {sig.parameters[name].default!r}"
        )


def test_log_trade_submitted_parameter_count_pin() -> None:
    sig = inspect.signature(audit_log_service.log_trade_submitted)
    expected = len(_REQUIRED_PARAMS) + len(_OPTIONAL_PARAMS_WITH_DEFAULTS)
    actual = len(sig.parameters)
    assert actual == expected, (
        f"log_trade_submitted parameter count drift: expected {expected}, got {actual}. "
        f"Params: {list(sig.parameters)!r}"
    )
