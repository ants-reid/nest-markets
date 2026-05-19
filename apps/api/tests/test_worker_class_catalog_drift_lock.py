"""Drift-lock pin: SHA-256 source-byte hash of ``DataSyncScheduler`` +
catalog of worker classes that the scheduler imports.

Cycle 64 — MH-DRIFTLOCK-WORKER-CLASS-CATALOG.

Why this pin exists
-------------------
Cycle 62 byte-pinned every cron expression; cycle 63 byte-pinned both
auto-paper worker ``execute`` bodies.  But the scheduler module itself
is the wiring that connects job names to worker classes — silently
adding a 6th worker, swapping the trader class for a different
implementation, or removing a registration would not flip the existing
pins.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import hashlib
import inspect

from app.schedules.data_sync_scheduler import DataSyncScheduler

EXPECTED_SCHEDULER_HASH = (
    "3618e546432ade86f22201b7f9467cce951e0158770973754a59f18557bb67ec"
)
EXPECTED_SCHEDULER_BYTE_LEN = 1691

# Module-import catalog: which worker classes are imported into the
# scheduler module. Frozen names + import paths.
EXPECTED_WORKER_IMPORTS: dict[str, str] = {
    "AutoPaperCloseWorker": "app.workers.auto_paper_close_worker",
    "AutoPaperTraderWorker": "app.workers.auto_paper_trader_worker",
    "DataSyncWorker": "app.workers.data_sync_worker",
    "NewsIngestWorker": "app.workers.news_ingest_worker",
    "SignalSweepWorker": "app.workers.signal_sweep_worker",
}

# Hard safety subset — workers whose import MUST remain.
SAFETY_WORKER_IMPORTS: dict[str, str] = {
    "AutoPaperCloseWorker": "app.workers.auto_paper_close_worker",
    "AutoPaperTraderWorker": "app.workers.auto_paper_trader_worker",
    "SignalSweepWorker": "app.workers.signal_sweep_worker",
}


def _hash(obj) -> tuple[str, int]:
    src = inspect.getsource(obj).encode("utf-8")
    return hashlib.sha256(src).hexdigest(), len(src)


def test_data_sync_scheduler_source_hash_unchanged() -> None:
    actual_hash, actual_len = _hash(DataSyncScheduler)
    assert (actual_hash, actual_len) == (
        EXPECTED_SCHEDULER_HASH,
        EXPECTED_SCHEDULER_BYTE_LEN,
    ), (
        "DataSyncScheduler source-byte drift detected.\n"
        f"  expected: sha256={EXPECTED_SCHEDULER_HASH} size={EXPECTED_SCHEDULER_BYTE_LEN}\n"
        f"  actual:   sha256={actual_hash} size={actual_len}\n"
        "Scheduler edits silently change which workers run on which "
        "cadence. ANY structural change MUST update the hash in the "
        "same PR with a ledger entry."
    )


def test_scheduler_module_imports_full_worker_catalog() -> None:
    import app.schedules.data_sync_scheduler as mod

    src = inspect.getsource(mod)
    drift: list[str] = []
    for cls_name, mod_path in EXPECTED_WORKER_IMPORTS.items():
        # Match the canonical `from <mod_path> import <cls_name>` line.
        needle = f"from {mod_path} import {cls_name}"
        if needle not in src:
            drift.append(f"  missing import: `{needle}`")
    assert not drift, (
        "DataSyncScheduler no longer imports the expected worker "
        "classes. The cron-expression catalog test (cycle 62) and "
        "worker-execute pin (cycle 63) assume these wirings.\n"
        + "\n".join(drift)
    )


def test_scheduler_module_imports_safety_subset() -> None:
    """Subset sanity: SAFETY_WORKER_IMPORTS must be a subset of the
    full catalog and all imports must be present."""
    import app.schedules.data_sync_scheduler as mod

    src = inspect.getsource(mod)
    for cls_name, mod_path in SAFETY_WORKER_IMPORTS.items():
        assert EXPECTED_WORKER_IMPORTS.get(cls_name) == mod_path, (
            f"Safety subset entry {cls_name}={mod_path} disagrees with "
            f"full catalog entry {EXPECTED_WORKER_IMPORTS.get(cls_name)!r}"
        )
        needle = f"from {mod_path} import {cls_name}"
        assert needle in src, (
            f"Safety-critical worker import missing from scheduler: {needle}"
        )


def test_scheduler_class_is_subclass_of_base() -> None:
    """Defensive: scheduler must remain a BaseScheduler subclass so
    ``list_jobs()`` continues to work (used by the cron-catalog test)."""
    from app.schedules.base_scheduler import BaseScheduler

    assert issubclass(DataSyncScheduler, BaseScheduler), (
        "DataSyncScheduler is no longer a BaseScheduler subclass; "
        "the cron-catalog test (cycle 62) depends on .list_jobs()."
    )
