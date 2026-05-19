"""Drift-lock: PaperExecutionResult dataclass field catalog (cycle 70).

Pins the public ``PaperExecutionResult`` dataclass fields. Note: the
module currently defines this dataclass twice (once at the top, once
near the bottom — the second wins for ``module.PaperExecutionResult``
attribute lookup). This test pins the *resolved* attribute so a future
cleanup that removes one definition still has the same field set.

Test-only / additive.
"""

from __future__ import annotations

import dataclasses

from app.services.paper_execution_service import PaperExecutionResult

EXPECTED_FIELD_NAMES: tuple[str, ...] = (
    "execution_id",
    "status",
    "asset",
    "timeframe",
    "side",
    "qty",
    "notional",
    "stop_price",
    "target_price",
    "fill_price",
    "reason",
)

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"execution_id", "status", "asset", "side", "qty", "stop_price",
     "target_price"}
)


def test_paper_execution_result_field_catalog() -> None:
    actual = tuple(f.name for f in dataclasses.fields(PaperExecutionResult))
    assert actual == EXPECTED_FIELD_NAMES, (
        "PaperExecutionResult field catalog drift.\n"
        f"  expected: {EXPECTED_FIELD_NAMES}\n"
        f"  actual:   {actual}"
    )


def test_paper_execution_result_safety_fields_present() -> None:
    actual = {f.name for f in dataclasses.fields(PaperExecutionResult)}
    missing = SAFETY_REQUIRED_FIELDS - actual
    assert not missing, (
        f"PaperExecutionResult missing safety field(s): {sorted(missing)}."
    )


def test_paper_execution_result_is_frozen() -> None:
    assert dataclasses.is_dataclass(PaperExecutionResult)
    params = PaperExecutionResult.__dataclass_params__  # type: ignore[attr-defined]
    assert params.frozen, (
        "PaperExecutionResult must remain frozen=True to keep "
        "deterministic execution simulation results immutable."
    )
