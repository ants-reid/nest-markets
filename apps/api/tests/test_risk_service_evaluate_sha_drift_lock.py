"""MH-DRIFTLOCK-RISK-SERVICE-EVALUATE-SHA-PIN

SHA-256 source pin on ``RiskService.evaluate`` — the newer risk evaluator
that emits durable RiskDecision rows (line 159 path in risk_service.py).
Complements cycle 78's pin on the legacy ``RiskEvaluator.evaluate``.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.risk_service import RiskService

_EXPECTED_SHA = "58d2b554627f3ad4c12c503487a7b5f896f1e27fd4111ef6c7422f819284a4a4"
_EXPECTED_LEN = 2750


def _src_meta() -> tuple[str, int, str]:
    src = inspect.getsource(RiskService.evaluate)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src), src


def test_risk_service_evaluate_sha_pin() -> None:
    sha, length, _ = _src_meta()
    assert sha == _EXPECTED_SHA, (
        f"RiskService.evaluate SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert length == _EXPECTED_LEN, (
        f"RiskService.evaluate length drift: expected {_EXPECTED_LEN}, got {length}"
    )
