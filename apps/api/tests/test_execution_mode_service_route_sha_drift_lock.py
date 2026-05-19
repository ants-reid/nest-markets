"""MH-DRIFTLOCK-EXECUTION-MODE-SERVICE-ROUTE-SHA-PIN

SHA-256 source pin on ``ExecutionModeService.route`` — selects between
paper / confirm_live / auto_live / blocked. Any silent edit must be loud.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.execution_mode_service import ExecutionModeService

_EXPECTED_SHA = "eb5a595b43c0f68cbf393bc5f99213c20d22a72bd8c8276501f2a08f0651838e"
_EXPECTED_LEN = 512


def _src_meta() -> tuple[str, int, str]:
    src = inspect.getsource(ExecutionModeService.route)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src), src


def test_execution_mode_route_sha_pin() -> None:
    sha, length, _ = _src_meta()
    assert sha == _EXPECTED_SHA, (
        f"ExecutionModeService.route SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert length == _EXPECTED_LEN, (
        f"ExecutionModeService.route length drift: expected {_EXPECTED_LEN}, got {length}"
    )


def test_execution_mode_route_returns_decision_type() -> None:
    _, _, src = _src_meta()
    assert "ExecutionModeDecision" in src, (
        "ExecutionModeService.route must construct an ExecutionModeDecision."
    )
