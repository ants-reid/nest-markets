"""MH-DRIFTLOCK-RISK-DECISION-DATACLASS-SCHEMA-PIN

Pins ``app.services.risk_service.RiskDecision`` dataclass: frozen=True
and exact field set. Distinct from the existing ``risk_decisions`` SQL
table catalog drift-lock (cycle 34) — this one pins the in-memory
return value of ``RiskService.evaluate`` / ``RiskEvaluator.evaluate``.
"""
from __future__ import annotations

import dataclasses

from app.services.risk_service import RiskDecision

_EXPECTED_FIELDS: frozenset[str] = frozenset(
    {"approved", "blocked_reasons", "allowed_risk_amount", "selected_execution_mode"}
)


def test_risk_decision_dataclass_is_frozen() -> None:
    assert dataclasses.is_dataclass(RiskDecision), "RiskDecision must remain a dataclass."
    assert RiskDecision.__dataclass_params__.frozen is True, (
        "RiskDecision must remain frozen=True so risk decisions are immutable."
    )


def test_risk_decision_dataclass_field_set_pin() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(RiskDecision))
    assert actual == _EXPECTED_FIELDS, (
        f"RiskDecision dataclass field drift. "
        f"missing={sorted(_EXPECTED_FIELDS - actual)} "
        f"extra={sorted(actual - _EXPECTED_FIELDS)}"
    )
