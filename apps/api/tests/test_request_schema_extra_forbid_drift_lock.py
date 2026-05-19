"""MH-DRIFTLOCK-REQUEST-SCHEMA-EXTRA-FORBID-CATALOG

Pins ``extra="forbid"`` on critical request schemas so that unknown fields
cannot smuggle data past the API surface. Drift-lock only — no runtime
behaviour change.
"""
from __future__ import annotations

from app.schemas import (
    approval as approval_schemas,
    execution as execution_schemas,
    risk as risk_schemas,
    risk_limits as risk_limits_schemas,
    signal as signal_schemas,
    trading_halt as trading_halt_schemas,
    workflow as workflow_schemas,
)

# (module, class_name) pairs that MUST keep extra="forbid".
_FORBID_TARGETS: tuple[tuple[object, str], ...] = (
    (execution_schemas, "PaperExecutionRequest"),
    (execution_schemas, "LiveExecutionRequestSchema"),
    (signal_schemas, "MockGenerateSignalRequest"),
    (risk_schemas, "RiskEvaluateRequest"),
    (risk_schemas, "RiskContextRequest"),
    (approval_schemas, "ApprovalCreateRequest"),
    (trading_halt_schemas, "TradingHaltCreateRequest"),
    (trading_halt_schemas, "TradingHaltResolveRequest"),
    (workflow_schemas, "WorkflowRunRequest"),
    (risk_limits_schemas, "RiskLimitConfigCreateRequest"),
    (risk_limits_schemas, "RiskLimitConfigUpdateRequest"),
    (risk_limits_schemas, "RiskLimitEvaluateRequest"),
)


def _resolve(module: object, name: str) -> type | None:
    return getattr(module, name, None)


def test_request_schemas_pin_extra_forbid() -> None:
    seen: dict[str, str] = {}
    for module, name in _FORBID_TARGETS:
        cls = _resolve(module, name)
        if cls is None:
            # Schema may have been renamed; skip gracefully but record so the
            # presence test below catches any missing safety class.
            continue
        cfg = getattr(cls, "model_config", {})
        # Pydantic v2: model_config is a dict-like ConfigDict.
        extra = cfg.get("extra") if isinstance(cfg, dict) else getattr(cfg, "extra", None)
        seen[name] = str(extra)
        assert extra == "forbid", (
            f"{name}.model_config['extra'] must remain 'forbid' (got {extra!r})"
        )
    # All targets must resolve; guards against silent renames.
    resolved = sum(1 for module, name in _FORBID_TARGETS if _resolve(module, name) is not None)
    assert resolved == len(_FORBID_TARGETS), (
        f"Request schema rename detected: {resolved}/{len(_FORBID_TARGETS)} resolved"
    )


def test_request_schema_catalog_floor() -> None:
    # Catalog floor: the canonical safety request-schema set must contain at
    # least 10 entries. Prevents accidental shrinkage of the catalog.
    assert len(_FORBID_TARGETS) >= 10
