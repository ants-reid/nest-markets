"""Drift-lock pin: SHA-256 source-byte hash of ``app.main._lifespan``.

Cycle 62 — MH-DRIFTLOCK-LIFESPAN-SOURCE-PIN.

Why this pin exists
-------------------
Cycle 61's ``test_lifespan_log_floor_drift_lock.py`` pins specific
log-line substrings + their levels.  This cycle adds a structural
byte-pin so that *any* edit to the lifespan body (not just removal of
those specific substrings) requires explicit hash recomputation.
Together they detect both "log line silently removed" and "lifespan
body silently restructured around the log line".

Cycles 59 + 60 already byte-pin six functions
(``assert_auto_trading_allowed``, ``assert_order_submission_allowed``,
``BrokerService.submit_auto_order``,
``BrokerService._submit_order_for_intent``,
``get_broker_mode_metadata``, ``assert_live_trading_armed``).  This
extends the pattern to the startup orchestration itself.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.

Updating after a legitimate edit
--------------------------------
Recompute via::

    PYTHONPATH=. .venv/bin/python -c "
    import hashlib, inspect
    from app import main
    print(hashlib.sha256(inspect.getsource(main._lifespan)
                         .encode('utf-8')).hexdigest())"

and update EXPECTED_HASH below in the SAME PR with a ledger entry.
"""

from __future__ import annotations

import hashlib
import inspect

from app import main as app_main


# Pinned at cycle 62.
EXPECTED_LIFESPAN_HASH = (
    "11535b048137286802244038392877c514ed9372fa5a237dce5f52c0e0ba884c"
)
EXPECTED_LIFESPAN_BYTE_LEN = 8633


def _hash_lifespan() -> tuple[str, int]:
    src = inspect.getsource(app_main._lifespan).encode("utf-8")
    return hashlib.sha256(src).hexdigest(), len(src)


def test_lifespan_source_hash_unchanged() -> None:
    actual_hash, actual_len = _hash_lifespan()
    assert (actual_hash, actual_len) == (
        EXPECTED_LIFESPAN_HASH,
        EXPECTED_LIFESPAN_BYTE_LEN,
    ), (
        "app.main._lifespan source-byte drift detected.\n"
        f"  expected: sha256={EXPECTED_LIFESPAN_HASH} size={EXPECTED_LIFESPAN_BYTE_LEN}\n"
        f"  actual:   sha256={actual_hash} size={actual_len}\n"
        "The lifespan function orchestrates scheduler startup, broker "
        "mode logging, and the broker tickle job. ANY structural edit "
        "MUST be reviewed and the new hash recorded in the same PR."
    )


def test_lifespan_is_async_generator_function() -> None:
    """Defensive: lifespan must remain an async-generator-style context "
    "manager (FastAPI's lifespan contract). A silent conversion to a
    plain ``def`` would break the lifespan binding without changing
    log substrings."""
    src = inspect.getsource(app_main._lifespan)
    assert src.lstrip().startswith(("async def", "@asynccontextmanager")) or (
        "@asynccontextmanager" in src and "async def _lifespan" in src
    ), (
        "_lifespan no longer presents as an async context manager. "
        "FastAPI requires the lifespan to be an async generator wrapped "
        "in @asynccontextmanager."
    )


def test_lifespan_callable_attribute_present() -> None:
    """Sanity guard: import surface unchanged."""
    assert hasattr(app_main, "_lifespan")
    assert callable(app_main._lifespan)
