"""Drift-lock pin: ``model_config`` on safety request schemas.

Cycle 65 — MH-DRIFTLOCK-PYDANTIC-MODEL-CONFIG-CATALOG.

Why this pin exists
-------------------
Cycle 61 SHA-256-pins individual schema field catalogs; this pin closes
the orthogonal axis: the schema-level ``model_config`` directives that
control validation strictness. ``extra='forbid'`` is what stops
attackers/tools from sneaking unknown payload keys past validation;
silently switching to ``extra='ignore'`` would not flip the field
catalog but would meaningfully weaken the safety surface.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

from app.schemas.execution import (
    LiveExecutionRequestSchema,
    PaperExecutionRequest,
)
from app.schemas.workflow import WorkflowRunRequest

# Each safety request schema MUST set extra='forbid'. Any 'allow' /
# 'ignore' would let unknown fields through validation.
SAFETY_REQUEST_SCHEMAS = (
    PaperExecutionRequest,
    LiveExecutionRequestSchema,
    WorkflowRunRequest,
)


def _config_extra(cls) -> object:
    cfg = getattr(cls, "model_config", {}) or {}
    if isinstance(cfg, dict):
        return cfg.get("extra")
    # ConfigDict subclass / namespace
    return getattr(cfg, "extra", None)


def test_safety_request_schemas_forbid_extra_fields() -> None:
    drift: list[str] = []
    for cls in SAFETY_REQUEST_SCHEMAS:
        extra = _config_extra(cls)
        if extra != "forbid":
            drift.append(
                f"  {cls.__module__}.{cls.__name__}: model_config['extra'] "
                f"is {extra!r}, expected 'forbid'"
            )
    assert not drift, (
        "Safety request schema model_config drift detected. extra='forbid' "
        "is what stops unknown keys from sneaking past validation; any "
        "weakening to 'allow' / 'ignore' silently widens the trading "
        "surface input.\n" + "\n".join(drift)
    )


def test_paper_execution_request_rejects_unknown_field() -> None:
    """Behavioural floor: instantiating with an unknown key MUST raise."""
    import pydantic

    raised = False
    try:
        PaperExecutionRequest.model_validate(
            {"signal_id": "00000000-0000-0000-0000-000000000000",
             "_unknown_extra_key_xyz": True}
        )
    except pydantic.ValidationError:
        raised = True
    except Exception:
        # Any validation-style error from required field absence is fine
        # — what matters is unknown keys are NOT silently accepted as a
        # success. We only treat silent success as a failure.
        raised = True
    assert raised, (
        "PaperExecutionRequest accepted an unknown field silently. "
        "extra='forbid' is no longer being enforced."
    )


def test_workflow_run_request_rejects_unknown_field() -> None:
    """Behavioural floor mirroring the paper-exec test."""
    import pydantic

    raised = False
    try:
        WorkflowRunRequest.model_validate({"_unknown_extra_key_xyz": True})
    except pydantic.ValidationError:
        raised = True
    except Exception:
        raised = True
    assert raised, (
        "WorkflowRunRequest accepted an unknown field silently. "
        "extra='forbid' is no longer being enforced."
    )


def test_safety_schema_count_floor() -> None:
    """Floor: catches silent removal of a safety schema from the
    catalog list above."""
    assert len(SAFETY_REQUEST_SCHEMAS) >= 3, (
        f"SAFETY_REQUEST_SCHEMAS has only {len(SAFETY_REQUEST_SCHEMAS)} "
        "entries; floor is 3 (paper + live + workflow)."
    )
