"""MH-DRIFTLOCK-SIGNAL-OUTPUT-DATACLASS-SCHEMA-PIN

Pins ``signal_service.SignalOutput``: frozen=True and the 17-field set.
SignalOutput is the LLM-emitted signal contract that downstream risk +
execution layers consume; silent shape drift could quietly drop fields
that gates depend on (``should_trade``, ``stop_price`` etc.).
"""
from __future__ import annotations

import dataclasses

from app.services.signal_service import SignalOutput

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {
        "asset",
        "timeframe",
        "direction",
        "regime",
        "setup_type",
        "entry_zone",
        "stop_price",
        "target_price",
        "confidence",
        "horizon_label",
        "catalyst_type",
        "catalyst_score",
        "catalyst_summary",
        "thesis",
        "invalidators",
        "signal_score",
        "should_trade",
    }
)
# Subset that gates / safety logic depends on. If the broader set drifts we
# still want to be loud about the safety-critical names disappearing.
_SAFETY_FIELDS: frozenset[str] = frozenset(
    {"should_trade", "stop_price", "target_price", "direction", "signal_score"}
)


def test_signal_output_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(SignalOutput)
    assert SignalOutput.__dataclass_params__.frozen is True, (
        "SignalOutput must remain frozen=True."
    )


def test_signal_output_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(SignalOutput))
    assert actual == _EXPECTED_FIELDS, (
        f"SignalOutput field drift. missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )


def test_signal_output_safety_fields_present() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(SignalOutput))
    missing = _SAFETY_FIELDS - actual
    assert not missing, (
        f"SignalOutput dropped safety-critical fields {sorted(missing)} — "
        "downstream gates depend on these."
    )
