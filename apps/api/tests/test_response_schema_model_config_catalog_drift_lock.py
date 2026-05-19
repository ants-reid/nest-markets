"""Drift-lock: response-schema model_config catalog (cycle 66).

Pins ``model_config={'extra': 'forbid'}`` on the three safety RESPONSE
schemas. A response schema that silently accepts unknown fields could
let a downstream caller smuggle in trading-control-style fields without
the Pydantic layer noticing.

Test-only / additive. No app code is changed.
"""

from __future__ import annotations

import pytest

from app.schemas.execution import (
    LiveExecutionResponse,
    PaperExecutionResponse,
)
from app.schemas.workflow import WorkflowRunResponse

SAFETY_RESPONSE_SCHEMAS = (
    PaperExecutionResponse,
    LiveExecutionResponse,
    WorkflowRunResponse,
)


def test_safety_response_schemas_forbid_extra_fields() -> None:
    drift: list[str] = []
    for cls in SAFETY_RESPONSE_SCHEMAS:
        cfg = getattr(cls, "model_config", {})
        extra = cfg.get("extra") if isinstance(cfg, dict) else None
        if extra != "forbid":
            drift.append(
                f"  {cls.__name__}: model_config['extra']={extra!r} "
                "(expected 'forbid')"
            )
    assert not drift, (
        "Safety RESPONSE schema model_config drift detected. Removing "
        "extra='forbid' on a response schema lets unknown keys leak "
        "through serialization round-trips.\n" + "\n".join(drift)
    )


def test_paper_execution_response_rejects_unknown_field() -> None:
    base = {
        "execution_id": "00000000-0000-0000-0000-000000000000",
        "status": "filled",
        "asset": "AAPL",
        "timeframe": "1d",
        "side": "long",
        "qty": 1.0,
        "notional": 100.0,
        "stop_price": 95.0,
        "target_price": 110.0,
        "fill_price": 100.0,
    }
    # Sanity: base payload is accepted.
    PaperExecutionResponse.model_validate(base)
    # Hard guard: unknown field is rejected.
    with pytest.raises(Exception):
        PaperExecutionResponse.model_validate({**base, "_smuggle": True})


def test_live_execution_response_rejects_unknown_field() -> None:
    base = {
        "accepted": False,
        "status": "disabled",
        "reason": "live_execution_disabled_in_mvp",
        "processed_at": "2025-01-01T00:00:00+00:00",
    }
    LiveExecutionResponse.model_validate(base)
    with pytest.raises(Exception):
        LiveExecutionResponse.model_validate({**base, "_smuggle": "x"})


def test_safety_response_schema_count_floor() -> None:
    assert len(SAFETY_RESPONSE_SCHEMAS) >= 3, (
        "SAFETY_RESPONSE_SCHEMAS shrank below the cycle-66 floor of 3."
    )
