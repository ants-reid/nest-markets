"""Drift-lock: ExecutionPolicy SQLA column catalog (cycle 73).

Pins the columns of the table that captures per-asset-class
execution policy (allow_long, allow_short, paper_only,
requires_user_confirmation).

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.execution_policy import ExecutionPolicy

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "allow_long",
        "allow_short",
        "allowed_timeframes_json",
        "asset_class",
        "created_at",
        "id",
        "mode",
        "paper_only",
        "requires_user_confirmation",
    }
)
SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"id", "asset_class", "mode", "paper_only",
     "requires_user_confirmation", "allow_long", "allow_short"}
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in ExecutionPolicy.__table__.columns)


def test_execution_policy_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "ExecutionPolicy column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_execution_policy_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"ExecutionPolicy missing safety column(s): {sorted(missing)}. "
        "These are the per-policy switches that gate live submission."
    )
