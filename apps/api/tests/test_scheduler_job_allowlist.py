"""MH-WORKER-RUN-AUDIT-DECORATOR-TEST — Scheduler job-name allow-list.

Drift-lock invariant: the production scheduler in
``apps/api/app/main.py`` plus the ``DataSyncScheduler`` registry must
register ONLY the documented set of background jobs. Any silently
introduced new job is a behaviour drift that must be reviewed under a
named matrix phase.

This test runs as a static AST scan of the source files so it is
independent of ``APP_ENV`` (the scheduler is disabled under
``APP_ENV=test``).

Drift-lock notes:
    * Pure additive test; no production code change.
    * No imports of trading_control_service, BrokerService, or worker
      runtime paths.
"""

from __future__ import annotations

import ast
from pathlib import Path

import app.main as main_module
import app.schedules.data_sync_scheduler as scheduler_module


# Documented allow-list. To add a new job:
#   1. Update this set in a SEPARATE phase.
#   2. Add a matrix row + ledger entry justifying the new job.
#   3. Confirm drift-lock impact in the ledger.
ALLOWED_SCHEDULER_JOB_IDS: frozenset[str] = frozenset(
    {
        # DataSyncScheduler-registered jobs (see data_sync_scheduler.py)
        "data_sync",
        "news_ingest",
        "signal_sweep",
        "auto_paper_trader",
        "auto_paper_close",
        "historical_import",
        "learning_trainer",
        # main.py-registered jobs
        "pnl_snapshot_capture",
        "broker_tickle",
    }
)


def _collect_string_kwargs(source: str, kwarg_name: str) -> set[str]:
    """Return all string-literal values passed as ``kwarg_name=`` in a source file."""
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == kwarg_name and isinstance(kw.value, ast.Constant):
                    if isinstance(kw.value.value, str):
                        found.add(kw.value.value)
    return found


def test_main_py_scheduler_add_job_ids_are_allowlisted():
    """Every literal ``id="..."`` passed to ``scheduler.add_job(...)`` in
    ``main.py`` must appear in the documented allow-list."""
    src = Path(main_module.__file__).read_text(encoding="utf-8")
    # ``id=`` strings include both APScheduler add_job ids AND unrelated
    # ``id=`` kwargs elsewhere — but main.py's ``id=`` usage is exclusively
    # for scheduler registrations (verified manually). If a future edit
    # adds an ``id=`` kwarg in a non-scheduler context, this test will
    # flag it; that is the intended drift signal.
    literal_ids = _collect_string_kwargs(src, "id")
    unexpected = literal_ids - ALLOWED_SCHEDULER_JOB_IDS
    assert not unexpected, (
        f"main.py registers scheduler ``id=`` literal(s) not in the "
        f"allow-list: {sorted(unexpected)}. If this is intentional, add "
        f"the new job to ALLOWED_SCHEDULER_JOB_IDS in a separate matrix "
        f"phase + ledger entry."
    )


def test_data_sync_scheduler_registers_only_allowlisted_jobs():
    """Every literal ``name="..."`` passed to ``ScheduledJob(...)`` in
    ``data_sync_scheduler.py`` must appear in the documented allow-list."""
    src = Path(scheduler_module.__file__).read_text(encoding="utf-8")
    literal_names = _collect_string_kwargs(src, "name")
    unexpected = literal_names - ALLOWED_SCHEDULER_JOB_IDS
    assert not unexpected, (
        f"data_sync_scheduler.py registers ``name=`` literal(s) not in "
        f"the allow-list: {sorted(unexpected)}. If this is intentional, "
        f"add the new job to ALLOWED_SCHEDULER_JOB_IDS in a separate "
        f"matrix phase + ledger entry."
    )


def test_data_sync_scheduler_runtime_registry_matches_allowlist():
    """Construct a ``DataSyncScheduler`` and verify ``list_jobs()``
    returns names that are all in the allow-list. Catches drift between
    static names and runtime registration."""
    sched = scheduler_module.DataSyncScheduler()
    runtime_names = {job.name for job in sched.list_jobs()}
    unexpected = runtime_names - ALLOWED_SCHEDULER_JOB_IDS
    assert not unexpected, (
        f"DataSyncScheduler.list_jobs() returns name(s) not in the "
        f"allow-list: {sorted(unexpected)}."
    )
    # Sanity: at least the data_sync job must register
    assert "data_sync" in runtime_names


def test_no_new_scheduler_module_added():
    """Ensure no second scheduler module has been silently introduced
    alongside ``data_sync_scheduler.py`` under ``app/schedules/``."""
    schedules_dir = Path(scheduler_module.__file__).parent
    py_files = {
        p.name
        for p in schedules_dir.glob("*.py")
        if p.name not in {"__init__.py"}
    }
    expected = {"base_scheduler.py", "data_sync_scheduler.py"}
    unexpected = py_files - expected
    assert not unexpected, (
        f"Unexpected scheduler module(s) under app/schedules/: "
        f"{sorted(unexpected)}. New scheduler files require a matrix "
        f"phase + ledger entry."
    )
