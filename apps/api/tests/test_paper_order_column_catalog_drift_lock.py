"""Drift-lock: PaperOrder SQLAlchemy column catalog (cycle 71).

Pins the column names of the ``PaperOrder`` ORM model — the table
that records every paper order's lifecycle. Renaming
``broker_order_id`` to ``order_id`` would silently break broker
status reconciliation.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.paper_order import PaperOrder

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "asset_id",
        "avg_fill_price",
        "broker_order_id",
        "commission",
        "created_at",
        "direction",
        "filled_quantity",
        "ibkr_status",
        "id",
        "limit_price",
        "notional",
        "order_type",
        "qty",
        "quantity",
        "risk_decision_id",
        "side",
        "signal_id",
        "status",
        "stop_price",
        "submitted_at",
        "timestamp",
        "updated_at",
    }
)

SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "asset_id",
        "risk_decision_id",
        "broker_order_id",
        "status",
        "direction",
        "quantity",
        "submitted_at",
    }
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in PaperOrder.__table__.columns)


def test_paper_order_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "PaperOrder column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration and update "
        "EXPECTED_COLUMNS."
    )


def test_paper_order_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"PaperOrder missing safety/reconciliation column(s): "
        f"{sorted(missing)}."
    )
