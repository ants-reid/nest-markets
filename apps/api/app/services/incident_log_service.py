"""MH-MON-05 — Incident log service.

Append-only writer + paginated reader. All writes are idempotent inserts (the
caller may pass an explicit ``occurred_at``; persistence ``created_at`` is
always set by the database).

Drift-lock guarantee: this service never modifies any trading control or any
table other than ``incident_logs``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models.incident_log import IncidentLog

VALID_SEVERITIES = ("info", "warn", "error", "critical")
Severity = Literal["info", "warn", "error", "critical"]


class IncidentLogError(ValueError):
    """Raised when an incident-log write is rejected (validation failure)."""


@dataclass(frozen=True)
class IncidentRow:
    id: str
    severity: str
    code: str
    title: str
    detail: Optional[str]
    source: str
    extra_json: Optional[Dict[str, Any]]
    correlation_id: Optional[str]
    occurred_at: Optional[str]
    created_at: str

    @classmethod
    def from_orm(cls, row: IncidentLog) -> "IncidentRow":
        return cls(
            id=str(row.id),
            severity=row.severity,
            code=row.code,
            title=row.title,
            detail=row.detail,
            source=row.source,
            extra_json=row.extra_json,
            correlation_id=row.correlation_id,
            occurred_at=row.occurred_at.isoformat() if row.occurred_at else None,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "code": self.code,
            "title": self.title,
            "detail": self.detail,
            "source": self.source,
            "extra_json": self.extra_json,
            "correlation_id": self.correlation_id,
            "occurred_at": self.occurred_at,
            "created_at": self.created_at,
        }


def _validate(severity: str, code: str, title: str, source: str) -> None:
    if severity not in VALID_SEVERITIES:
        raise IncidentLogError(
            f"severity must be one of {VALID_SEVERITIES}, got {severity!r}"
        )
    if not code or len(code) > 80:
        raise IncidentLogError("code must be non-empty and ≤ 80 chars")
    if not title or len(title) > 255:
        raise IncidentLogError("title must be non-empty and ≤ 255 chars")
    if not source or len(source) > 64:
        raise IncidentLogError("source must be non-empty and ≤ 64 chars")


def record_incident(
    session: Session,
    *,
    severity: Severity,
    code: str,
    title: str,
    source: str,
    detail: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> IncidentRow:
    """Append a single incident row. Returns the persisted row."""
    _validate(severity, code, title, source)
    row = IncidentLog(
        severity=severity,
        code=code,
        title=title,
        detail=detail,
        source=source,
        extra_json=extra,
        correlation_id=correlation_id,
        occurred_at=occurred_at,
        # Explicit per-row timestamp (microsecond resolution) so multiple
        # inserts in the same transaction order deterministically. The DB
        # default ``now()`` is transaction-time and would tie rows.
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return IncidentRow.from_orm(row)


def list_incidents(
    session: Session,
    *,
    limit: int = 100,
    severity: Optional[Severity] = None,
    source: Optional[str] = None,
) -> List[IncidentRow]:
    """Read-most-recent incidents (DESC by created_at). Capped at 500 rows."""
    capped = max(1, min(int(limit), 500))
    stmt = (
        select(IncidentLog)
        .order_by(desc(IncidentLog.created_at), desc(IncidentLog.id))
        .limit(capped)
    )
    if severity is not None:
        if severity not in VALID_SEVERITIES:
            raise IncidentLogError(f"invalid severity filter: {severity!r}")
        stmt = stmt.where(IncidentLog.severity == severity)
    if source is not None:
        stmt = stmt.where(IncidentLog.source == source)
    rows = session.execute(stmt).scalars().all()
    return [IncidentRow.from_orm(r) for r in rows]
