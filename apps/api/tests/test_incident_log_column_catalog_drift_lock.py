"""Drift-lock: IncidentLog SQLA column catalog (cycle 73).

Pins the columns of the durable incident-record table. The
``correlation_id`` column is the join key for tracing a trade
incident back to the originating request.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.incident_log import IncidentLog

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {"code", "correlation_id", "created_at", "detail", "extra_json",
     "id", "occurred_at", "severity", "source", "title"}
)
SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"id", "code", "severity", "source", "occurred_at",
     "correlation_id"}
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in IncidentLog.__table__.columns)


def test_incident_log_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "IncidentLog column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_incident_log_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"IncidentLog missing safety/trace column(s): {sorted(missing)}."
    )
