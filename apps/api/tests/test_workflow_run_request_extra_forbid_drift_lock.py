"""MH-DRIFTLOCK-WORKFLOW-RUN-REQUEST-EXTRA-FORBID

Pins ``WorkflowRunRequest.model_config['extra'] == 'forbid'`` and the
field set, so silent loosening of the workflow request schema cannot
let unknown fields slip past validation.
"""
from __future__ import annotations

from app.schemas.workflow import WorkflowRunRequest

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {"risk_context", "signal_input", "use_mock_signal"}
)


def test_workflow_run_request_extra_forbid() -> None:
    cfg = getattr(WorkflowRunRequest, "model_config", None) or {}
    extra = cfg.get("extra") if isinstance(cfg, dict) else None
    assert extra == "forbid", (
        f"WorkflowRunRequest.model_config.extra drift: expected 'forbid', got {extra!r}."
    )


def test_workflow_run_request_field_floor() -> None:
    actual = frozenset(WorkflowRunRequest.model_fields.keys())
    missing = _EXPECTED_FIELDS - actual
    assert not missing, f"WorkflowRunRequest lost required fields: {sorted(missing)}"
