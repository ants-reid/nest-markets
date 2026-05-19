"""Drift-lock: WorkflowResult dataclass field catalog (cycle 68).

Pins fields of ``app.services.workflow_service.WorkflowResult``.

Safety-critical fields:
* ``risk_approved`` — boolean gate; removal silently treats every
  workflow as risk-approved.
* ``blocked_reasons`` — list that callers consume to surface WHY a
  workflow was blocked. Removing it would silently drop the reason
  trail.
* ``selected_execution_mode`` — used by routes to decide which
  execution surface to call.

Test-only / additive.
"""

from __future__ import annotations

import dataclasses

from app.services.workflow_service import WorkflowResult

EXPECTED_WORKFLOW_RESULT_FIELDS: tuple[str, ...] = (
    "signal_id",
    "risk_approved",
    "selected_execution_mode",
    "approval_request_id",
    "paper_execution_id",
    "blocked_reasons",
    "live_execution_result",
)

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"risk_approved", "selected_execution_mode", "blocked_reasons"}
)


def _field_names() -> tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(WorkflowResult))


def test_workflow_result_field_catalog_exact_match() -> None:
    actual = _field_names()
    assert actual == EXPECTED_WORKFLOW_RESULT_FIELDS, (
        "WorkflowResult field-catalog drift detected.\n"
        f"  expected: {EXPECTED_WORKFLOW_RESULT_FIELDS}\n"
        f"  actual:   {actual}\n"
        "If intentional, update EXPECTED_WORKFLOW_RESULT_FIELDS and "
        "audit every consumer in app/api/routes/workflow.py."
    )


def test_safety_required_fields_present() -> None:
    actual = set(_field_names())
    missing = SAFETY_REQUIRED_FIELDS - actual
    assert not missing, (
        f"WorkflowResult is missing safety-required field(s): {sorted(missing)}. "
        "These three fields are how downstream callers discover the "
        "risk verdict, the chosen execution surface, and any blockers."
    )
