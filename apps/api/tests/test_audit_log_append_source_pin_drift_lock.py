"""MH-DRIFTLOCK-AUDIT-LOG-APPEND-SHA-PIN

SHA-256 source pin on ``audit_log_service._append``. The body is small and
stable (mkdir + open append + json.dumps + write). Any change is a contract
shift on the durable trail.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services import audit_log_service

_EXPECTED_SHA = "e351c6d48f2e40fb9f0b073685b7c6aca09e521e64c4ff949a04e09acb956ac7"
_EXPECTED_LEN = 318


def _src_meta() -> tuple[str, int, str]:
    src = inspect.getsource(audit_log_service._append)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src), src


def test_audit_log_append_source_sha_pin() -> None:
    sha, length, _ = _src_meta()
    assert sha == _EXPECTED_SHA, (
        f"audit_log_service._append SHA drift: expected {_EXPECTED_SHA}, got {sha}. "
        "If this change is intentional, review the durable-trail contract and "
        "update the pin under an explicit drift-lock cycle."
    )
    assert length == _EXPECTED_LEN, (
        f"audit_log_service._append length drift: expected {_EXPECTED_LEN}, got {length}"
    )


def test_audit_log_append_required_tokens_present() -> None:
    _, _, src = _src_meta()
    for tok in ('open("a"', "json.dumps", "mkdir(parents=True, exist_ok=True)"):
        assert tok in src, f"Audit append token missing: {tok!r}"
