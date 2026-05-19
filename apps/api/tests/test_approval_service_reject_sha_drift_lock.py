"""MH-DRIFTLOCK-APPROVAL-SERVICE-REJECT-SHA-PIN

SHA-256 source pin on ``ApprovalService.reject``.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.approval_service import ApprovalService

_EXPECTED_SHA = "75566dec950bb4768512407fb8c5e3ade18024feaadd7cc4a5918268085f2260"
_EXPECTED_LEN = 156


def test_approval_service_reject_sha_pin() -> None:
    src = inspect.getsource(ApprovalService.reject)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"ApprovalService.reject SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert len(src) == _EXPECTED_LEN, (
        f"ApprovalService.reject length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )
