"""Drift-lock: SignalOutput dataclass field catalog (cycle 68).

Pins fields of ``app.services.signal_service.SignalOutput``.

Safety-critical fields:
* ``should_trade`` — boolean gate consumed by every downstream
  execution path. Removal would silently treat all signals as
  tradable.
* ``direction`` / ``stop_price`` / ``target_price`` — without these,
  paper / live execution paths cannot construct an order at all.

Test-only / additive.
"""

from __future__ import annotations

import dataclasses

from app.services.signal_service import SignalOutput

EXPECTED_SIGNAL_OUTPUT_FIELDS: tuple[str, ...] = (
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
)

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"asset", "direction", "stop_price", "target_price", "should_trade"}
)


def _field_names() -> tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(SignalOutput))


def test_signal_output_field_catalog_exact_match() -> None:
    actual = _field_names()
    assert actual == EXPECTED_SIGNAL_OUTPUT_FIELDS, (
        "SignalOutput field-catalog drift detected.\n"
        f"  expected: {EXPECTED_SIGNAL_OUTPUT_FIELDS}\n"
        f"  actual:   {actual}\n"
        "If intentional, update EXPECTED_SIGNAL_OUTPUT_FIELDS and "
        "audit every consumer in app/services and app/api/routes."
    )


def test_safety_required_fields_present() -> None:
    actual = set(_field_names())
    missing = SAFETY_REQUIRED_FIELDS - actual
    assert not missing, (
        f"SignalOutput is missing safety-required field(s): {sorted(missing)}. "
        "Removing should_trade silently makes every signal tradable; "
        "removing stop/target prevents risk-bounded order construction."
    )


def test_should_trade_field_is_boolean_typed() -> None:
    """Hard guard: should_trade must remain a bool. A change to e.g.
    ``str`` would let truthy strings ("no") slip through as True.
    """
    fields = {f.name: f for f in dataclasses.fields(SignalOutput)}
    field = fields["should_trade"]
    assert field.type in (bool, "bool"), (
        f"SignalOutput.should_trade type drift: {field.type!r} "
        "(expected bool). Truthy non-bool values would silently slip "
        "the trade gate."
    )
