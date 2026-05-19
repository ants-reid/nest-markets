"""Drift-lock pin: byte-for-byte cron expressions on every scheduled job.

Cycle 62 — MH-DRIFTLOCK-CRON-EXPRESSION-CATALOG.

Why this pin exists
-------------------
Cycle 59's ``test_worker_registry_drift_lock.py`` already pins job
NAMES + their cron expressions in a single tuple.  This file is a
narrower, byte-level pin focused exclusively on cron *shape*: catches
silent retiming like ``*/5 * * * *`` → ``* * * * *`` (12× more runs)
or ``0 */4 * * *`` → ``0 * * * *`` (4× more runs).  Even though cycle
59 already covers this, having a dedicated focused test makes a
retiming regression self-explanatory.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

from app.schedules.data_sync_scheduler import DataSyncScheduler


# Job-name -> exact cron string.  Frozen at cycle 62.
EXPECTED_CRON_EXPRESSIONS: dict[str, str] = {
    "data_sync": "*/5 * * * *",
    "news_ingest": "0 * * * *",
    "signal_sweep": "0 */4 * * *",
    "auto_paper_trader": "30 */4 * * *",
    "auto_paper_close": "0 2 * * *",
}

# Subset whose cron form is part of the safety contract.  Speeding any
# of these up silently increases auto-paper / signal-evaluation cadence.
SAFETY_CRON_JOBS: set[str] = {
    "auto_paper_trader",
    "auto_paper_close",
    "signal_sweep",
}


def _collect_actual_crons() -> dict[str, str]:
    sched = DataSyncScheduler()
    return {job.name: job.cron for job in sched.list_jobs()}


def test_cron_expression_catalog_exact_match() -> None:
    actual = _collect_actual_crons()
    missing = set(EXPECTED_CRON_EXPRESSIONS) - set(actual)
    extra = set(actual) - set(EXPECTED_CRON_EXPRESSIONS)
    assert not missing and not extra, (
        f"Scheduled-job name set drift. Missing: {sorted(missing)}. "
        f"Extra: {sorted(extra)}."
    )
    failures: list[str] = []
    for name, expected_cron in EXPECTED_CRON_EXPRESSIONS.items():
        actual_cron = actual[name]
        if actual_cron != expected_cron:
            failures.append(
                f"  {name}: expected cron={expected_cron!r} got={actual_cron!r}"
            )
    assert not failures, (
        "Cron-expression byte drift detected. Retiming a job changes its "
        "execution cadence directly.\n" + "\n".join(failures)
    )


def test_safety_cron_jobs_use_4h_or_daily_cadence() -> None:
    """Defensive: the safety-cadence jobs must NOT be retimed to a
    higher frequency than every-4h (or 02:00 daily for the close job).

    A silent edit to ``"*/5 * * * *"`` on auto_paper_trader would 48×
    its run rate.
    """
    actual = _collect_actual_crons()
    high_freq_patterns = ("* * * * *", "*/1", "*/2", "*/3", "*/5", "*/10", "*/15", "*/30")
    failures: list[str] = []
    for name in SAFETY_CRON_JOBS:
        cron = actual[name]
        # Match on first field (minute) form to detect sub-hour cadence.
        first_field = cron.split()[0] if cron else ""
        # Allow only minute-literals (00..59) or hour-positional minutes
        # (e.g. "30" in "30 */4 * * *", "0" in "0 2 * * *", "0" in
        # "0 */4 * * *"). Reject any "*/N" or "*" in the minute slot.
        if first_field == "*" or first_field.startswith("*/"):
            failures.append(
                f"  {name}: minute-field {first_field!r} indicates sub-hour "
                f"cadence (full cron={cron!r})"
            )
        else:
            # Also reject explicit any of the high-frequency patterns
            # appearing anywhere in the cron string.
            for hp in high_freq_patterns:
                if hp in cron:
                    failures.append(
                        f"  {name}: cron contains high-frequency pattern "
                        f"{hp!r} (full cron={cron!r})"
                    )
                    break
    assert not failures, (
        "Safety-critical cron job cadence regression. Speeding up these "
        "jobs silently changes auto-paper / signal-evaluation rates.\n"
        + "\n".join(failures)
    )


def test_safety_cron_subset_is_subset_of_full_catalog() -> None:
    missing = SAFETY_CRON_JOBS - set(EXPECTED_CRON_EXPRESSIONS)
    assert not missing, (
        f"SAFETY_CRON_JOBS contains entries not in EXPECTED_CRON_EXPRESSIONS: "
        f"{sorted(missing)}"
    )
