"""MH-COCKPIT-06-A — Notifications digest aggregator.

Read-only aggregator over the existing append-only ``incident_logs`` table
that produces a compact "needs attention" payload suitable for an in-app
notifications drawer. It returns the highest-severity recent incidents plus
per-severity counts, distinct from the raw ``/monitor/incidents`` feed.

Drift-lock guarantees:
- Pure SELECT over ``incident_logs``.
- Never writes, never reads from any trading-control / broker / worker /
  signal table.
- Never feeds the trading path; output is operator-facing only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models.incident_log import IncidentLog
from app.services.incident_log_service import VALID_SEVERITIES

_SEVERITY_RANK: Dict[str, int] = {
    "critical": 4,
    "error": 3,
    "warn": 2,
    "info": 1,
}

_DEFAULT_HOURS = 24
_MIN_HOURS = 1
_MAX_HOURS = 24 * 7
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50


class NotificationsDigestError(ValueError):
    """Raised when the caller passes invalid digest parameters."""


def _row_payload(row: IncidentLog) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "severity": row.severity,
        "code": row.code,
        "title": row.title,
        "source": row.source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "occurred_at": (
            row.occurred_at.isoformat() if row.occurred_at else None
        ),
    }


def get_notifications_digest(
    session: Session,
    *,
    hours: int = _DEFAULT_HOURS,
    min_severity: str = "warn",
    limit: int = _DEFAULT_LIMIT,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return a compact notifications digest.

    Parameters
    ----------
    hours:
        Lookback window in hours. Clamped to ``[1, 168]``.
    min_severity:
        Severity floor for the "attention" list. Counts include all
        severities; the `attention` list only includes rows ≥ this rank.
    limit:
        Max number of attention rows to return. Clamped to ``[1, 50]``.
    now_utc:
        Test hook for window upper bound.
    """
    if not isinstance(hours, int) or hours < _MIN_HOURS:
        raise NotificationsDigestError("hours must be a positive integer")
    if hours > _MAX_HOURS:
        hours = _MAX_HOURS
    if min_severity not in _SEVERITY_RANK:
        raise NotificationsDigestError(
            f"min_severity must be one of {tuple(_SEVERITY_RANK)}, "
            f"got {min_severity!r}"
        )
    capped_limit = max(1, min(int(limit), _MAX_LIMIT))

    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    window_start = now - timedelta(hours=hours)

    base_stmt = (
        select(IncidentLog)
        .where(IncidentLog.created_at >= window_start)
        .where(IncidentLog.created_at <= now)
    )

    # All rows in window — for counts.
    all_rows = session.execute(
        base_stmt.order_by(desc(IncidentLog.created_at), desc(IncidentLog.id))
    ).scalars().all()

    counts: Dict[str, int] = {sev: 0 for sev in VALID_SEVERITIES}
    by_source: Dict[str, int] = {}
    for row in all_rows:
        sev = row.severity if row.severity in counts else "info"
        counts[sev] += 1
        by_source[row.source] = by_source.get(row.source, 0) + 1

    floor_rank = _SEVERITY_RANK[min_severity]
    attention_severities = [
        sev for sev, rank in _SEVERITY_RANK.items() if rank >= floor_rank
    ]

    attention_rows = [
        r for r in all_rows if r.severity in attention_severities
    ][:capped_limit]

    # Highest current severity present in window.
    highest = "none"
    for sev in ("critical", "error", "warn", "info"):
        if counts.get(sev, 0) > 0:
            highest = sev
            break

    return {
        "as_of_utc": now.isoformat(),
        "window_start_utc": window_start.isoformat(),
        "hours": hours,
        "min_severity": min_severity,
        "limit": capped_limit,
        "advisory": (
            "Notifications digest is derived from the append-only incident "
            "log and is operator-facing only. It never feeds the trading "
            "path."
        ),
        "totals": {
            "incidents": sum(counts.values()),
            "by_severity": counts,
            "by_source": by_source,
        },
        "attention_count": len(attention_rows),
        "highest_severity": highest,
        "attention": [_row_payload(r) for r in attention_rows],
    }
