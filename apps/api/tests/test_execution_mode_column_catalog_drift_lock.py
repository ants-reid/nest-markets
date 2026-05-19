"""Drift-lock: ExecutionMode SQLA column catalog (cycle 73).

Pins the columns of the table that controls per-mode policy
(allows_live_orders, requires_approval). Renaming
``allows_live_orders`` to ``live_orders`` would silently flip the
gate's meaning at the ORM layer.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.execution_mode import ExecutionMode

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {"allows_live_orders", "created_at", "id", "is_active", "name",
     "requires_approval"}
)
SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"id", "name", "is_active", "allows_live_orders", "requires_approval"}
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in ExecutionMode.__table__.columns)


def test_execution_mode_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "ExecutionMode column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_execution_mode_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"ExecutionMode missing safety column(s): {sorted(missing)}."
    )
