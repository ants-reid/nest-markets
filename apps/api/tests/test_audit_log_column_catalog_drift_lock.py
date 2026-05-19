"""Drift-lock: AuditLog SQLAlchemy column catalog (cycle 71).

Pins the column names of the ``AuditLog`` ORM model — the table that
PaperExecutionService writes order_created / order_filled events to.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.audit_log import AuditLog

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "created_at",
        "entity_id",
        "entity_type",
        "event_type",
        "id",
        "payload_json",
    }
)

SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"id", "entity_type", "entity_id", "event_type", "payload_json",
     "created_at"}
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in AuditLog.__table__.columns)


def test_audit_log_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "AuditLog column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_audit_log_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"AuditLog missing safety column(s): {sorted(missing)}."
    )
