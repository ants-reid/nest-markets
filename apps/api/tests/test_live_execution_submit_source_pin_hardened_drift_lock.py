"""MH-DRIFTLOCK-LIVE-EXECUTION-SUBMIT-SHA-HARDEN

Hardens cycle 74's token pin into a SHA-256 source pin on
``LiveExecutionService.submit``. Any silent edit to the Gate 4 routing body
will flip the SHA loud.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.live_execution_service import LiveExecutionService

_EXPECTED_SHA = "522b38f0e79282ab0620b20c9e25c112ae1b8c2ce120c84f002d50d475a02824"
_EXPECTED_LEN = 2696


def _src_meta() -> tuple[str, int]:
    src = inspect.getsource(LiveExecutionService.submit)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src)


def test_live_execution_submit_source_sha_hardened() -> None:
    sha, length = _src_meta()
    assert sha == _EXPECTED_SHA, (
        f"LiveExecutionService.submit SHA drift: expected {_EXPECTED_SHA}, got {sha}. "
        "Gate 4 body changed — review carefully before updating the pin."
    )
    assert length == _EXPECTED_LEN, (
        f"LiveExecutionService.submit length drift: expected {_EXPECTED_LEN}, got {length}"
    )
