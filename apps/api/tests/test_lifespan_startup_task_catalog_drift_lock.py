"""Drift-lock: lifespan startup-task catalog (cycle 71).

Source-text scan for the literal ``id="..."`` strings used in
``scheduler.add_job(...)`` calls inside ``app.main._lifespan``.
Adding or removing a startup job would silently change runtime
scheduling without touching DataSyncScheduler.

Test-only / additive — does not execute the lifespan.
"""

from __future__ import annotations

import inspect
import re

from app import main as app_main

# Job IDs added by lifespan (DataSyncScheduler jobs use job.name as
# id; explicit ids appear for ad-hoc lifespan-only jobs).
EXPECTED_LIFESPAN_AD_HOC_JOB_IDS: frozenset[str] = frozenset(
    {"broker_tickle"}
)

# DataSyncScheduler job names that lifespan iterates over and
# registers as their own ids (replace_existing=True).
EXPECTED_DATA_SYNC_JOB_IDS: frozenset[str] = frozenset(
    {
        "auto_paper_close",
        "auto_paper_trader",
        "data_sync",
        "news_ingest",
        "signal_sweep",
    }
)


def _lifespan_source() -> str:
    return inspect.getsource(app_main._lifespan)


def test_lifespan_registers_ad_hoc_jobs() -> None:
    src = _lifespan_source()
    ids_in_src = set(re.findall(r'id\s*=\s*[\"\']([\w_]+)[\"\']', src))
    missing = EXPECTED_LIFESPAN_AD_HOC_JOB_IDS - ids_in_src
    assert not missing, (
        "Lifespan is no longer registering safety-relevant ad-hoc "
        f"job(s): {sorted(missing)}. Removing broker_tickle would "
        "let the IBKR session expire silently."
    )


def test_lifespan_iterates_data_sync_jobs() -> None:
    """Source must reference DataSyncScheduler and a list_jobs loop."""
    src = _lifespan_source()
    assert "DataSyncScheduler" in src, (
        "Lifespan no longer instantiates DataSyncScheduler — "
        "scheduled jobs would not be registered with APScheduler."
    )
    assert "list_jobs" in src, (
        "Lifespan no longer iterates DataSyncScheduler.list_jobs() — "
        "auto_paper_trader would never be scheduled."
    )


def test_lifespan_test_env_short_circuit_intact() -> None:
    """When APP_ENV=='test', no scheduler must start — this is the
    invariant that prevents background jobs from interfering with
    pytest. Pin the literal guard.
    """
    src = _lifespan_source()
    assert 'APP_ENV' in src and '"test"' in src, (
        "Lifespan no longer guards on APP_ENV != 'test'. Background "
        "scheduler would attempt to run during pytest."
    )


def test_lifespan_emits_broker_safety_warning() -> None:
    """The startup safety-posture log must remain so operators can
    confirm live execution is not silently armed.
    """
    src = _lifespan_source()
    assert "BROKER SAFETY WARNING" in src, (
        "Lifespan no longer emits the BROKER SAFETY WARNING log line; "
        "operators would lose the at-startup tripwire that surfaces "
        "accidental live-execution configuration."
    )
    assert "BROKER MODE" in src, (
        "Lifespan no longer emits the BROKER MODE info log; "
        "safety posture is no longer printed at startup."
    )
