"""Drift-lock: pin the registered scheduler/worker job catalog.

Cycle 59 — MH-DRIFTLOCK-WORKER-REGISTRY (pure additive test-only).

Two job-name surfaces are pinned:

1. ``DataSyncScheduler`` — declares its job catalog via
   ``register_job(ScheduledJob(name=..., cron=..., enabled=...))``.
   These are the cron-driven worker entry points exercised by the
   APScheduler ``AsyncIOScheduler`` started in ``app.main._lifespan``.
2. Lifecycle-only jobs added directly inside ``app.main._lifespan`` via
   ``scheduler.add_job(..., id=...)``: ``broker_tickle``,
   ``pnl_snapshot_capture``, plus the special-cased ``signal_sweep``
   interval registration and the ``auto_paper_trader`` cron registration
   (both of which appear in the ``DataSyncScheduler`` catalog with their
   declared cron, but are mounted by main with overrides).

A new auto-execution worker, or a new lifespan job that could touch the
broker, would require an additive entry here AND an explicit ledger entry
explaining why it does not weaken the drift-lock.

Drift-lock guarantees
---------------------
* Read-only test — does not start the scheduler, does not run any
  worker, does not touch the DB or the broker.
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

import inspect

from app.schedules.data_sync_scheduler import DataSyncScheduler


# Pinned catalog of jobs declared by DataSyncScheduler (cron-managed).
# Tuple shape: (name, cron, enabled).
EXPECTED_DATA_SYNC_JOBS: set[tuple[str, str, bool]] = {
    ("data_sync", "*/5 * * * *", True),
    ("news_ingest", "0 * * * *", True),
    ("signal_sweep", "0 */4 * * *", True),
    ("auto_paper_trader", "30 */4 * * *", True),
    ("auto_paper_close", "0 2 * * *", True),
}

# Pinned set of LITERAL ``id="..."`` tokens that ``app.main._lifespan``
# registers directly on the scheduler (i.e. lifespan-only jobs that are
# NOT declared inside DataSyncScheduler). The DataSyncScheduler-managed
# jobs use ``id=job.name`` (a variable) and are pinned separately by
# EXPECTED_DATA_SYNC_JOBS. Adding any new lifespan-only job — especially
# one that interacts with the broker — must be paired with a ledger
# entry and an additive update to this set.
EXPECTED_LIFESPAN_JOB_IDS: set[str] = {
    "broker_tickle",
    "pnl_snapshot_capture",
}

# Subset that is safety-critical: jobs that, if added/removed silently,
# could change the auto-trading or auto-paper posture of the system.
SAFETY_CRITICAL_JOB_NAMES: set[str] = {
    "auto_paper_trader",  # gated worker — must remain in catalog
    "auto_paper_close",   # paper liquidator
    "signal_sweep",       # generates the candidates the trader consumes
    "broker_tickle",      # broker session keep-alive
    "pnl_snapshot_capture",  # captures realised P&L for safety review
}


def _collect_data_sync_jobs() -> set[tuple[str, str, bool]]:
    sched = DataSyncScheduler()
    return {(j.name, j.cron, j.enabled) for j in sched.list_jobs()}


def _collect_lifespan_job_ids() -> set[str]:
    """Extract every ``id="..."`` token from the source of ``_lifespan``."""
    from app import main as main_module
    src = inspect.getsource(main_module._lifespan)
    # Also include the helper that registers pnl_snapshot_capture.
    src += inspect.getsource(main_module._register_pnl_snapshot_scheduler)
    ids: set[str] = set()
    # naive but durable: split on ``id="`` and read up to the next ``"``
    parts = src.split('id="')
    for p in parts[1:]:
        end = p.find('"')
        if end > 0:
            ids.add(p[:end])
    return ids


def test_data_sync_scheduler_job_catalog_exact_match() -> None:
    actual = _collect_data_sync_jobs()
    missing = EXPECTED_DATA_SYNC_JOBS - actual
    extra = actual - EXPECTED_DATA_SYNC_JOBS
    assert not missing and not extra, (
        "DataSyncScheduler job catalog drift detected. "
        f"Missing (in catalog, not declared): {sorted(missing)}. "
        f"Extra (declared, not in catalog): {sorted(extra)}. "
        "Update tests/test_worker_registry_drift_lock.py::"
        "EXPECTED_DATA_SYNC_JOBS and append a build-ledger entry "
        "explaining the new or removed job. New auto-execution jobs "
        "must additionally pass the drift-lock review."
    )


def test_lifespan_job_id_catalog_exact_match() -> None:
    actual = _collect_lifespan_job_ids()
    missing = EXPECTED_LIFESPAN_JOB_IDS - actual
    extra = actual - EXPECTED_LIFESPAN_JOB_IDS
    assert not missing and not extra, (
        "Lifespan-registered job-ID drift detected in app.main._lifespan. "
        f"Missing: {sorted(missing)}. Extra: {sorted(extra)}. "
        "Any new scheduler.add_job(..., id=...) inside the lifespan must "
        "be paired with an additive entry in EXPECTED_LIFESPAN_JOB_IDS."
    )


def test_safety_critical_job_names_present_in_data_sync_or_lifespan() -> None:
    data_sync_names = {n for (n, _, _) in _collect_data_sync_jobs()}
    lifespan_ids = _collect_lifespan_job_ids()
    union = data_sync_names | lifespan_ids
    missing = SAFETY_CRITICAL_JOB_NAMES - union
    assert not missing, (
        "Safety-critical job(s) silently removed from the scheduler "
        f"surface: {sorted(missing)}. These jobs guard auto-paper, "
        "auto-trading, broker session keep-alive, or P&L capture; "
        "their removal must be a deliberate, ledger-tracked phase."
    )


def test_no_unexpected_auto_or_live_trading_job_added() -> None:
    """Sanity floor: no job whose id starts with ``auto_`` or ``live_``
    may exist outside the pinned catalogs. Catches attempts to silently
    add e.g. ``auto_live_trader`` or ``auto_broker_submit``.
    """
    data_sync_names = {n for (n, _, _) in _collect_data_sync_jobs()}
    lifespan_ids = _collect_lifespan_job_ids()
    suspicious = {
        n for n in (data_sync_names | lifespan_ids)
        if n.startswith("auto_") or n.startswith("live_")
    }
    allowed_auto_or_live = {
        "auto_paper_trader",
        "auto_paper_close",
    }
    unexpected = suspicious - allowed_auto_or_live
    assert not unexpected, (
        f"Unexpected auto_/live_ scheduler job(s) registered: "
        f"{sorted(unexpected)}. Adding an auto-execution or live "
        "trading job requires an explicit drift-lock unlock and a "
        "matching update to allowed_auto_or_live in this test."
    )
