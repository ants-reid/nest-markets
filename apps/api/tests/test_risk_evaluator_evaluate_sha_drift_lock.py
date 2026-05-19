"""MH-DRIFTLOCK-RISK-EVALUATOR-EVALUATE-SHA-PIN

SHA-256 source pin on ``RiskEvaluator.evaluate`` — the durable
risk-decision producer that emits ``RiskDecision`` rows. Edits must be loud.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.risk_service import RiskEvaluator

_EXPECTED_SHA = "a4198c98e54a8e05c3967ec5e51da08f56017bf62d6d168e6f8157cea83b739c"
_EXPECTED_LEN = 694


def _src_meta() -> tuple[str, int, str]:
    src = inspect.getsource(RiskEvaluator.evaluate)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src), src


def test_risk_evaluator_evaluate_sha_pin() -> None:
    sha, length, _ = _src_meta()
    assert sha == _EXPECTED_SHA, (
        f"RiskEvaluator.evaluate SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert length == _EXPECTED_LEN, (
        f"RiskEvaluator.evaluate length drift: expected {_EXPECTED_LEN}, got {length}"
    )


def test_risk_evaluator_evaluate_returns_risk_decision() -> None:
    _, _, src = _src_meta()
    assert "RiskDecision(" in src, (
        "RiskEvaluator.evaluate must construct a RiskDecision."
    )
    assert "_collect_blocked_reasons" in src, (
        "RiskEvaluator.evaluate must collect blocked reasons before returning."
    )
