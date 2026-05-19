"""MH-DRIFTLOCK-AUDIT-LOG-APPEND-SAFETY-TOKEN-PIN

Token-level guard on ``audit_log_service._append`` body. Complements the
cycle-76 byte-exact SHA pin: even a SHA-clean refactor that left the
function the same byte-count but accidentally dropped append-mode (``"a"``)
or utf-8 encoding would now fail loudly.
"""
from __future__ import annotations

import inspect

from app.services import audit_log_service

_REQUIRED_TOKENS: tuple[str, ...] = (
    '"a"',           # append mode — never overwrite the trail
    'encoding="utf-8"',
    "json.dumps",
    "_AUDIT_LOG_PATH",
)


def test_audit_log_append_safety_tokens_present() -> None:
    src = inspect.getsource(audit_log_service._append)
    missing = [t for t in _REQUIRED_TOKENS if t not in src]
    assert not missing, (
        f"audit_log_service._append lost safety tokens {missing!r}. "
        "These tokens enforce append-only writes, utf-8 encoding, and the canonical path const."
    )
