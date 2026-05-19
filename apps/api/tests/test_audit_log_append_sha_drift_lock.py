"""MH-DRIFTLOCK-AUDIT-LOG-APPEND-SHA-PIN

Byte-exact SHA-256 pin on ``audit_log_service._append``. Complements
the cycle-82 token pin (tokens guarantee specific strings appear);
this pin guarantees the entire body is byte-for-byte unchanged.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services import audit_log_service

_EXPECTED_SHA = "e351c6d48f2e40fb9f0b073685b7c6aca09e521e64c4ff949a04e09acb956ac7"
_EXPECTED_LEN = 318


def test_audit_log_append_sha_pin() -> None:
    src = inspect.getsource(audit_log_service._append)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"audit_log_service._append SHA drift: expected {_EXPECTED_SHA}, got {sha}. "
        "Any change to the audit append path must be reviewed against the append-only contract."
    )
    assert len(src) == _EXPECTED_LEN, (
        f"audit_log_service._append length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )
