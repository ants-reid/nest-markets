"""Drift-lock pin: SHA-256 source-byte hashes of broker-mode-guard helpers.

Cycle 60 — MH-DRIFTLOCK-BROKER-MODE-GUARD-SOURCE-PIN.

Why this pin exists
-------------------
Cycle 59 hash-pinned the four trading-control gates
(``assert_auto_trading_allowed``, ``assert_order_submission_allowed``,
``BrokerService.submit_auto_order``, ``BrokerService._submit_order_for_intent``).
This cycle extends the same byte-level pin to the two adjacent surfaces
that decide *which broker mode is active* and *whether live trading has
been armed*:

    app.services.broker_mode_guard.get_broker_mode_metadata
    app.services.trading_control_service.assert_live_trading_armed

Either of these silently weakening (e.g. defaulting to live, removing the
"requires explicit arming" check) would bypass downstream gates that trust
their return values.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.

Updating after a legitimate edit
--------------------------------
If one of these functions is intentionally changed, recompute the hash::

    PYTHONPATH=. .venv/bin/python -c "
    import hashlib, inspect
    from app.services.broker_mode_guard import get_broker_mode_metadata
    print(hashlib.sha256(inspect.getsource(get_broker_mode_metadata)
                         .encode('utf-8')).hexdigest())"

and update EXPECTED_HASHES below in the SAME PR that changes the function,
adding a ledger entry that justifies the change.
"""

from __future__ import annotations

import hashlib
import inspect

from app.services.broker_mode_guard import get_broker_mode_metadata
from app.services.trading_control_service import assert_live_trading_armed

# Pinned at cycle 60.  Recompute and update in PR if the function body
# legitimately changes; the change MUST be reviewed.
EXPECTED_HASHES: dict[str, tuple[str, int]] = {
    "app.services.broker_mode_guard.get_broker_mode_metadata": (
        "344b3ca12ae0ce7f3772a46570c908a9c8585167f69510110fa81b8e3d82ef32",
        1179,
    ),
    "app.services.trading_control_service.assert_live_trading_armed": (
        "55cbb325f83247072c356fcb428f48dd2d981456598bc8ce90b85ac50a403c94",
        428,
    ),
}

_PINNED_FUNCS = (
    get_broker_mode_metadata,
    assert_live_trading_armed,
)


def _hash_source(fn) -> tuple[str, int]:
    src = inspect.getsource(fn).encode("utf-8")
    return hashlib.sha256(src).hexdigest(), len(src)


def test_broker_mode_guard_source_hashes_match() -> None:
    failures: list[str] = []
    for fn in _PINNED_FUNCS:
        qual = f"{fn.__module__}.{fn.__qualname__}"
        actual_hash, actual_size = _hash_source(fn)
        expected_hash, expected_size = EXPECTED_HASHES[qual]
        if (actual_hash, actual_size) != (expected_hash, expected_size):
            failures.append(
                f"  {qual}\n"
                f"    expected: sha256={expected_hash} size={expected_size}\n"
                f"    actual:   sha256={actual_hash} size={actual_size}"
            )
    assert not failures, (
        "Broker-mode-guard source-byte drift detected. These helpers decide "
        "which broker mode is active and whether live trading has been "
        "armed; downstream gates trust their return values. ANY change MUST "
        "be reviewed and the new hash recorded in the same PR.\n"
        + "\n".join(failures)
    )


def test_get_broker_mode_metadata_source_invariants() -> None:
    """Behavioural-substring guard: regardless of byte changes, the helper
    must continue to read its broker-mode signal from the database/service
    layer rather than hard-coding a 'live' default."""
    src = inspect.getsource(get_broker_mode_metadata)
    assert "metadata" in src.lower(), (
        "get_broker_mode_metadata must continue to expose mode metadata."
    )
    # Defensive: a future regression that hard-codes 'live' as the
    # unconditional return value would be a safety failure.
    assert 'return "live"' not in src and "return 'live'" not in src, (
        "get_broker_mode_metadata must NOT unconditionally return 'live'."
    )


def test_assert_live_trading_armed_source_invariants() -> None:
    """Behavioural-substring guard: the live-trading arming gate must
    continue to perform an explicit check (it must not become a no-op)."""
    src = inspect.getsource(assert_live_trading_armed)
    # The function exists to RAISE when live trading is not armed.  A
    # no-op (single ``return`` / ``pass``) body would silently allow live
    # orders.
    body_lines = [
        ln.strip() for ln in src.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    # Strip signature + docstring opener lines to get a fair signal.
    meaningful = [ln for ln in body_lines if not ln.startswith('"""')]
    assert len(meaningful) > 2, (
        "assert_live_trading_armed appears to have collapsed to a near-empty "
        "body. The function must continue to enforce the live-trading "
        "arming check."
    )
    # The function name implies it raises on disarmed; assert at least one
    # raise/exception construct remains.
    assert "raise" in src or "Error" in src, (
        "assert_live_trading_armed must continue to raise/return an error "
        "when live trading is not armed."
    )


def test_pinned_functions_are_callable_attributes() -> None:
    """Sanity guard: imports succeed and refer to the expected callables."""
    assert callable(get_broker_mode_metadata)
    assert callable(assert_live_trading_armed)
    assert (
        get_broker_mode_metadata.__module__
        == "app.services.broker_mode_guard"
    )
    assert (
        assert_live_trading_armed.__module__
        == "app.services.trading_control_service"
    )
