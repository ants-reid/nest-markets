"""Drift-lock: LiveExecutionRequest dataclass field catalog (cycle 70).

Pins the field names + types of the ``LiveExecutionRequest`` dataclass —
the contract the future broker submission path consumes. Renaming
``stop_price`` to ``stop`` would silently break the cycle-66 SHA pin's
caller without touching the function body itself.

Test-only / additive.
"""

from __future__ import annotations

import dataclasses
import typing

from app.services.live_execution_service import LiveExecutionRequest

EXPECTED_FIELDS: tuple[tuple[str, str], ...] = (
    ("asset", "str"),
    ("side", "Literal['buy', 'sell']"),
    ("qty", "float"),
    ("notional", "float"),
    ("stop_price", "float"),
    ("target_price", "float"),
    ("execution_mode", "str"),
)

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"asset", "side", "qty", "stop_price", "target_price", "execution_mode"}
)


def _normalize(s: str) -> str:
    return s.replace("typing.", "").replace('"', "'").replace(" ", "")


def test_live_execution_request_field_catalog() -> None:
    actual = tuple(
        (f.name, _normalize(str(f.type) if not isinstance(f.type, str) else f.type))
        for f in dataclasses.fields(LiveExecutionRequest)
    )
    expected_norm = tuple((n, _normalize(t)) for n, t in EXPECTED_FIELDS)
    assert actual == expected_norm, (
        "LiveExecutionRequest field catalog drift.\n"
        f"  expected: {expected_norm}\n"
        f"  actual:   {actual}\n"
        "If intentional, update EXPECTED_FIELDS and confirm broker "
        "submission callers still construct the request correctly."
    )


def test_live_execution_request_safety_fields_present() -> None:
    actual_names = {f.name for f in dataclasses.fields(LiveExecutionRequest)}
    missing = SAFETY_REQUIRED_FIELDS - actual_names
    assert not missing, (
        f"LiveExecutionRequest missing safety field(s): {sorted(missing)}."
    )


def test_live_execution_request_is_frozen() -> None:
    assert dataclasses.is_dataclass(LiveExecutionRequest)
    params = LiveExecutionRequest.__dataclass_params__  # type: ignore[attr-defined]
    assert params.frozen, (
        "LiveExecutionRequest must remain frozen=True to prevent "
        "mutation between validation and broker submission."
    )


def test_live_execution_request_side_literal_values() -> None:
    """Side must remain a buy/sell literal — no 'short_sell' or other variants."""
    hints = typing.get_type_hints(LiveExecutionRequest)
    side_type = hints["side"]
    args = typing.get_args(side_type)
    assert set(args) == {"buy", "sell"}, (
        f"LiveExecutionRequest.side literal drift: {args}"
    )
