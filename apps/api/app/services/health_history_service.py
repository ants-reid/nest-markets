"""MH-MON-08-A — Health-history aggregator.

Read-only aggregation over the existing append-only ``incident_logs`` table
(written via :mod:`app.services.incident_log_service`). Buckets incidents into
fixed-width time windows so the frontend can render hourly/quarter-hourly
counts per severity and per source.

Drift-lock guarantees:
- Pure SELECT. Never writes to any table.
- Never reads from any trading-control / broker / worker / signal table.
- Output is operator-facing only and never feeds the trading path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.incident_log import IncidentLog
from app.services.incident_log_service import VALID_SEVERITIES

_DEFAULT_HOURS = 24
_MAX_HOURS = 24 * 7  # one week
_MIN_HOURS = 1
_DEFAULT_BUCKET_MINUTES = 60
_ALLOWED_BUCKET_MINUTES = (15, 30, 60, 120, 240)


class HealthHistoryError(ValueError):
    """Raised when the caller passes invalid history parameters."""


def _bucket_start(ts: datetime, bucket_seconds: int, window_start: datetime) -> datetime:
    """Floor ``ts`` to the bucket boundary aligned to ``window_start``."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = (ts - window_start).total_seconds()
    if delta < 0:
        return window_start
    floored = int(delta // bucket_seconds) * bucket_seconds
    return window_start + timedelta(seconds=floored)


def get_health_history(
    session: Session,
    *,
    hours: int = _DEFAULT_HOURS,
    source: Optional[str] = None,
    bucket_minutes: int = _DEFAULT_BUCKET_MINUTES,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return time-bucketed incident counts.

    Parameters
    ----------
    hours:
        Window size in hours. Clamped to ``[1, 168]``.
    source:
        Optional ``source`` filter (e.g. ``"broker"``).
    bucket_minutes:
        Bucket width. Must be one of ``(15, 30, 60, 120, 240)``.
    now_utc:
        Override for the window upper bound (test hook).
    """
    if not isinstance(hours, int) or hours < _MIN_HOURS:
        raise HealthHistoryError("hours must be a positive integer")
    if hours > _MAX_HOURS:
        hours = _MAX_HOURS
    if bucket_minutes not in _ALLOWED_BUCKET_MINUTES:
        raise HealthHistoryError(
            f"bucket_minutes must be one of {_ALLOWED_BUCKET_MINUTES}, "
            f"got {bucket_minutes!r}"
        )

    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    window_start = now - timedelta(hours=hours)
    bucket_seconds = bucket_minutes * 60

    stmt = (
        select(IncidentLog)
        .where(IncidentLog.created_at >= window_start)
        .where(IncidentLog.created_at <= now)
        .order_by(IncidentLog.created_at.asc())
    )
    if source is not None:
        stmt = stmt.where(IncidentLog.source == source)
    rows = session.execute(stmt).scalars().all()

    # Pre-build empty buckets so the timeseries is dense.
    bucket_count = (hours * 3600) // bucket_seconds
    buckets: List[datetime] = [
        window_start + timedelta(seconds=i * bucket_seconds) for i in range(bucket_count)
    ]
    bucket_index = {b.isoformat(): i for i, b in enumerate(buckets)}

    severity_series: Dict[str, List[int]] = {
        sev: [0] * bucket_count for sev in VALID_SEVERITIES
    }
    source_totals: Dict[str, int] = {}
    severity_totals: Dict[str, int] = {sev: 0 for sev in VALID_SEVERITIES}
    last_per_source: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        bstart = _bucket_start(row.created_at, bucket_seconds, window_start)
        idx = bucket_index.get(bstart.isoformat())
        if idx is None:
            continue
        sev = row.severity if row.severity in severity_series else "info"
        severity_series[sev][idx] += 1
        severity_totals[sev] += 1
        source_totals[row.source] = source_totals.get(row.source, 0) + 1
        # Track most-recent (rows are ASC; overwrite as we iterate)
        last_per_source[row.source] = {
            "severity": row.severity,
            "code": row.code,
            "title": row.title,
            "created_at": row.created_at.isoformat(),
        }

    timeseries = [
        {
            "bucket_start": b.isoformat(),
            "counts": {sev: severity_series[sev][i] for sev in VALID_SEVERITIES},
            "total": sum(severity_series[sev][i] for sev in VALID_SEVERITIES),
        }
        for i, b in enumerate(buckets)
    ]

    return {
        "as_of_utc": now.isoformat(),
        "window_start_utc": window_start.isoformat(),
        "hours": hours,
        "bucket_minutes": bucket_minutes,
        "filters": {"source": source},
        "advisory": (
            "Health history is derived from append-only incident_logs and is "
            "operator-facing only. It never feeds the trading path."
        ),
        "totals": {
            "by_severity": severity_totals,
            "by_source": source_totals,
            "incidents": sum(severity_totals.values()),
        },
        "last_per_source": last_per_source,
        "timeseries": timeseries,
    }
