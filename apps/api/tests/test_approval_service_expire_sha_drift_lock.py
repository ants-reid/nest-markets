"""MH-DRIFTLOCK-APPROVAL-SERVICE-EXPIRE-SHA-PIN

SHA-256 source pin on ``ApprovalService.expire``.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.approval_service import ApprovalService

_EXPECTED_SHA = "3ba601c2569fef02eb065ec7cbb272c43943dd863c65d552c395a60fec21a1bd"
_EXPECTED_LEN = 350


def test_approval_service_expire_sha_pin() -> None:
    src = inspect.getsource(ApprovalService.expire)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"ApprovalService.expire SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert len(src) == _EXPECTED_LEN, (
        f"ApprovalService.expire length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )
