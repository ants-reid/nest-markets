"""MH-DRIFTLOCK-SIGNAL-INPUT-DATACLASS-SCHEMA-PIN

Pins ``signal_service.SignalInput``: frozen=True and the 6-field set.
SignalInput is the contract carrying feature_snapshot + catalyst_context
into the LLM signal generator; silent shape changes would alter the
prompt surface without a loud failure.
"""
from __future__ import annotations

import dataclasses

from app.services.signal_service import SignalInput

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {
        "feature_snapshot",
        "catalyst_context",
        "asset",
        "timeframe",
        "latest_price",
        "risk_notes",
    }
)


def test_signal_input_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(SignalInput)
    assert SignalInput.__dataclass_params__.frozen is True, (
        "SignalInput must remain frozen=True so the prompt-input cannot be mutated mid-flight."
    )


def test_signal_input_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(SignalInput))
    assert actual == _EXPECTED_FIELDS, (
        f"SignalInput field drift. missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )
