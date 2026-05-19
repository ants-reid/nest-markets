"""Drift-lock: CorrelationIDMiddleware SHA-256 source pin (cycle 72).

Pins the bytes of ``CorrelationIDMiddleware`` — the middleware that
assigns/echoes the per-request correlation id used by every audit
log line. A silent change here would break post-hoc trace-back of
trade events.

Test-only / additive.
"""

from __future__ import annotations

import hashlib
import inspect

from app.services.correlation_context import CorrelationIDMiddleware

EXPECTED_SHA = (
    "ecdecfc3758b1079db3570b5160540916c480c6d6e6e37b09faa1261f0d1bfd4"
)
EXPECTED_LEN = 795


def test_correlation_id_middleware_source_pinned() -> None:
    src = inspect.getsource(CorrelationIDMiddleware).encode("utf-8")
    actual_sha = hashlib.sha256(src).hexdigest()
    actual_len = len(src)
    assert (actual_sha, actual_len) == (EXPECTED_SHA, EXPECTED_LEN), (
        "CorrelationIDMiddleware source drift detected.\n"
        f"  expected: ({EXPECTED_SHA}, {EXPECTED_LEN})\n"
        f"  actual:   ({actual_sha}, {actual_len})\n"
        "If intentional, update EXPECTED_SHA and document the change "
        "in the build ledger — this middleware is on the request "
        "path of every API call."
    )
