"""MH-DRIFTLOCK-APPROVAL-SERVICE-CREATE-REQUEST-SHA-PIN

SHA-256 source pin on ``ApprovalService.create_request`` — gated entry point
that raises when risk is not approved. Silent edit must be loud.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.approval_service import ApprovalService

_EXPECTED_SHA = "a5197d2046ae2a68e24997dc5b4a84acdc545f6d8e46df1dcf5e7ec675002dba"
_EXPECTED_LEN = 632


def _src_meta() -> tuple[str, int, str]:
    src = inspect.getsource(ApprovalService.create_request)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src), src


def test_approval_service_create_request_sha_pin() -> None:
    sha, length, _ = _src_meta()
    assert sha == _EXPECTED_SHA, (
        f"ApprovalService.create_request SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert length == _EXPECTED_LEN, (
        f"ApprovalService.create_request length drift: expected {_EXPECTED_LEN}, got {length}"
    )
