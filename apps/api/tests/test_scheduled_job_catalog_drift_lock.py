"""Drift-lock: scheduled job catalog (cycle 70).

Pins the names + cron expressions of the cron-driven jobs registered
by ``DataSyncScheduler`` — these are the jobs that the lifespan hook
in ``app.main`` adds to APScheduler. Renaming ``auto_paper_trader``
or changing its cron would silently change auto-paper firing
cadence; this test makes that loud.

Drift-lock note: this test does NOT enable any worker; it only
inspects the static cron registry.

Test-only / additive.
"""

from __future__ import annotations

from app.schedules.data_sync_scheduler import DataSyncScheduler

EXPECTED_JOBS: dict[str, str] = {
    "auto_paper_close": "0 2 * * *",
    "auto_paper_trader": "30 */4 * * *",
    "data_sync": "*/5 * * * *",
    "news_ingest": "0 * * * *",
    "signal_sweep": "0 */4 * * *",
}

SAFETY_REQUIRED_JOB_NAMES: frozenset[str] = frozenset(
    {"auto_paper_close", "auto_paper_trader", "signal_sweep"}
)


def _jobs_by_name() -> dict[str, object]:
    return {j.name: j for j in DataSyncScheduler().list_jobs()}


def test_scheduled_job_catalog_exact() -> None:
    jobs = _jobs_by_name()
    actual = {name: jobs[name].cron for name in jobs}  # type: ignore[attr-defined]
    extra = set(actual) - set(EXPECTED_JOBS)
    missing = set(EXPECTED_JOBS) - set(actual)
    cron_drift = {
        n: (EXPECTED_JOBS[n], actual[n])
        for n in set(EXPECTED_JOBS) & set(actual)
        if EXPECTED_JOBS[n] != actual[n]
    }
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new job(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected job(s): {sorted(missing)}")
    if cron_drift:
        msg.append(f"  Cron drift: {cron_drift}")
    assert not msg, (
        "DataSyncScheduler job catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, update EXPECTED_JOBS and verify the "
        "lifespan hook in app/main.py still wires the new job into "
        "APScheduler."
    )


def test_safety_required_jobs_present_and_enabled() -> None:
    jobs = _jobs_by_name()
    for name in SAFETY_REQUIRED_JOB_NAMES:
        assert name in jobs, (
            f"Safety-required scheduled job missing: {name!r}."
        )
        # enabled is the registry-level toggle; the lifespan still
        # gates execution behind APP_ENV != 'test'.
        assert jobs[name].enabled, (  # type: ignore[attr-defined]
            f"Safety-required job {name!r} is disabled in registry."
        )
