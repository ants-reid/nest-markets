"""Drift-lock pin: SHA-256 source-byte hashes of the auto-paper worker
``execute`` methods, plus behavioural-substring guards that confirm
the workers still ROUTE THROUGH the auto-submit gate
(``BrokerService.submit_auto_order``) rather than bypassing it.

Cycle 63 — MH-DRIFTLOCK-WORKER-EXECUTE-SOURCE-PIN.

Why this pin exists
-------------------
``BrokerService.submit_auto_order`` itself is SHA-256-pinned (cycle 59)
and unconditionally calls ``assert_auto_trading_allowed()`` via
``_submit_order_for_intent``.  But that protection is only effective
if the auto-paper workers continue to *call* ``submit_auto_order``.
A silent worker rewrite that bypassed the gate (e.g. went direct to
the broker client) would defeat the entire trading-control chain
without altering ``trading_control_service.py`` or ``broker_service.py``.

This test pins the worker bodies that drive auto submission and
asserts the gate-call line still appears in their source.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.

Updating after a legitimate edit
--------------------------------
Recompute via::

    PYTHONPATH=. .venv/bin/python -c "
    import hashlib, inspect
    from app.workers.auto_paper_trader_worker import AutoPaperTraderWorker
    from app.workers.auto_paper_close_worker import AutoPaperCloseWorker
    for fn in (AutoPaperTraderWorker.execute, AutoPaperCloseWorker.execute):
        s = inspect.getsource(fn).encode('utf-8')
        print(hashlib.sha256(s).hexdigest(), len(s))"

Update EXPECTED_HASHES below in the same PR with a ledger entry.
"""

from __future__ import annotations

import hashlib
import inspect

from app.workers.auto_paper_close_worker import AutoPaperCloseWorker
from app.workers.auto_paper_trader_worker import AutoPaperTraderWorker

EXPECTED_HASHES: dict[str, tuple[str, int]] = {
    "AutoPaperTraderWorker.execute": (
        "b7930994375ae88d5e178309860e7f35223dbf128922a4833ba61b764633d17b",
        4889,
    ),
    "AutoPaperCloseWorker.execute": (
        "df6bf652d7d2adc6e1af9cd943c42b02b0d8e469633fef74dffe13a22d99e2cb",
        2676,
    ),
}

_TARGETS = {
    "AutoPaperTraderWorker.execute": AutoPaperTraderWorker.execute,
    "AutoPaperCloseWorker.execute": AutoPaperCloseWorker.execute,
}


def _hash(fn) -> tuple[str, int]:
    src = inspect.getsource(fn).encode("utf-8")
    return hashlib.sha256(src).hexdigest(), len(src)


def test_worker_execute_source_hashes_unchanged() -> None:
    drift: list[str] = []
    for name, fn in _TARGETS.items():
        actual = _hash(fn)
        expected = EXPECTED_HASHES[name]
        if actual != expected:
            drift.append(
                f"  {name}: expected sha256={expected[0]} size={expected[1]}; "
                f"actual sha256={actual[0]} size={actual[1]}"
            )
    assert not drift, (
        "Auto-paper worker .execute source-byte drift detected. ANY "
        "structural change to these methods MUST be reviewed and the new "
        "hash recorded in the same PR. The trading-control chain depends "
        "on these workers continuing to route through "
        "BrokerService.submit_auto_order().\n" + "\n".join(drift)
    )


def test_trader_worker_still_routes_through_auto_submit_gate() -> None:
    """Even if execute hash legitimately moves, the gate-call line must
    still appear in the trader worker's module source (the call may be
    refactored into a helper, hence module-scope check)."""
    import app.workers.auto_paper_trader_worker as mod

    src = inspect.getsource(mod)
    assert "submit_auto_order" in src, (
        "auto_paper_trader_worker.py no longer references "
        "BrokerService.submit_auto_order. The auto-submit gate "
        "(assert_auto_trading_allowed) MUST be invoked through this "
        "method; routing around it would silently disable the drift lock."
    )


def test_close_worker_does_not_introduce_auto_order_submission() -> None:
    """The close worker today does NOT submit new auto orders (it
    closes existing positions). Detect a regression that wires it to
    submit auto orders without explicit unlock."""
    import app.workers.auto_paper_close_worker as mod

    src = inspect.getsource(mod)
    assert "submit_auto_order" not in src, (
        "auto_paper_close_worker.py now references submit_auto_order. "
        "The close worker must not submit NEW auto orders; if this is "
        "intentional, obtain explicit drift-lock unlock and update this "
        "test."
    )


def test_worker_class_invariants() -> None:
    assert AutoPaperTraderWorker.worker_name == "auto_paper_trader"
    assert AutoPaperCloseWorker.worker_name == "auto_paper_close"
    for cls in (AutoPaperTraderWorker, AutoPaperCloseWorker):
        assert callable(getattr(cls, "execute", None)), (
            f"{cls.__name__} no longer exposes an execute() method; the "
            "BaseWorker contract relies on this."
        )
