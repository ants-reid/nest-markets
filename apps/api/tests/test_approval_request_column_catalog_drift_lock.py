"""Drift-lock: ApprovalRequest SQLA column catalog (cycle 73).

Pins the columns of the durable approval-decision record. Renaming
``approved_by`` would silently break audit attribution chains for
every approved trade.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.approval_request import ApprovalRequest

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "approved_at",
        "approved_by",
        "created_at",
        "expired_at",
        "expires_at",
        "id",
        "notes",
        "rejected_by",
        "requested_at",
        "responded_at",
        "responded_by",
        "risk_decision_id",
        "signal_id",
        "status",
        "timestamp",
    }
)
SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "signal_id",
        "risk_decision_id",
        "status",
        "approved_by",
        "approved_at",
        "rejected_by",
        "expires_at",
    }
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in ApprovalRequest.__table__.columns)


def test_approval_request_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "ApprovalRequest column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_approval_request_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"ApprovalRequest missing safety/attribution column(s): "
        f"{sorted(missing)}."
    )
