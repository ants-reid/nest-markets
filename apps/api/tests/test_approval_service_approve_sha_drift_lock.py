"""MH-DRIFTLOCK-APPROVAL-SERVICE-APPROVE-SHA-PIN

SHA-256 source pin on ``ApprovalService.approve``. State transition
pending→approved must not drift silently.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.approval_service import ApprovalService

_EXPECTED_SHA = "da192df519c04f1d80a377c3eb4ed4872ece9ceadb1d5d6e85eae69d55d6f8ad"
_EXPECTED_LEN = 157


def test_approval_service_approve_sha_pin() -> None:
    src = inspect.getsource(ApprovalService.approve)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"ApprovalService.approve SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert len(src) == _EXPECTED_LEN, (
        f"ApprovalService.approve length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )
