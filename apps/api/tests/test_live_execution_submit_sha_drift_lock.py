"""MH-DRIFTLOCK-LIVE-EXECUTION-SUBMIT-SHA-PIN

Byte-exact SHA-256 pin on ``LiveExecutionService.submit``.
Complements the cycle-81 token pin: tokens guarantee certain strings
appear; this pin guarantees the entire body is unchanged byte-for-byte.

Live execution is the highest-risk surface — it must not drift silently.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.live_execution_service import LiveExecutionService

_EXPECTED_SHA = "522b38f0e79282ab0620b20c9e25c112ae1b8c2ce120c84f002d50d475a02824"
_EXPECTED_LEN = 2696


def test_live_execution_submit_sha_pin() -> None:
    src = inspect.getsource(LiveExecutionService.submit)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"LiveExecutionService.submit SHA drift: expected {_EXPECTED_SHA}, got {sha}. "
        "Any change here must be reviewed against the live-trading kill-switch contract."
    )
    assert len(src) == _EXPECTED_LEN, (
        f"LiveExecutionService.submit length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )
