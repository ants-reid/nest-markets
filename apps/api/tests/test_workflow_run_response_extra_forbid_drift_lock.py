"""MH-DRIFTLOCK-WORKFLOW-RUN-RESPONSE-EXTRA-FORBID

Pins ``WorkflowRunResponse.model_config['extra'] == 'forbid'`` and the
field set, so silent loosening of the workflow response (e.g. adding
opaque pass-through data) cannot happen without a loud failure.
"""
from __future__ import annotations

from app.schemas.workflow import WorkflowRunResponse

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {
        "approval_request_id",
        "blocked_reasons",
        "live_execution_result",
        "paper_execution_id",
        "risk_approved",
        "selected_execution_mode",
        "signal_id",
    }
)


def test_workflow_run_response_extra_forbid() -> None:
    cfg = getattr(WorkflowRunResponse, "model_config", None) or {}
    extra = cfg.get("extra") if isinstance(cfg, dict) else None
    assert extra == "forbid", (
        f"WorkflowRunResponse.model_config.extra drift: expected 'forbid', got {extra!r}. "
        "Loosening to 'allow'/'ignore' would let unexpected fields slip through the workflow response."
    )


def test_workflow_run_response_field_floor() -> None:
    actual = frozenset(WorkflowRunResponse.model_fields.keys())
    missing = _EXPECTED_FIELDS - actual
    assert not missing, f"WorkflowRunResponse lost required fields: {sorted(missing)}"
