"""Cycle 41 — Schema drift-lock for ``paper_fills``.

Locks the simulated-fill record — the per-fill child of paper_orders.
With auto-paper enforcement OFF (per drift-lock), this table is
write-quiet today; pinning its shape now means any future fill writer
landing in MH-152 / MH-156 must ship additively.

Pinned shape:
  * 6 business columns, full nullability map
  * Numeric precision: fill_price/fill_qty/fee_amount=(18,8),
    slippage_bps=(10,4)
  * FK paper_order_id -> paper_orders.id (NOT NULL — every fill must
    be tied to an order)

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric

from app.db.models.paper_fill import PaperFill


# (nullable, type)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type]] = {
    "paper_order_id": (False, type(None)),  # UUID FK
    "fill_ts": (False, DateTime),
    "fill_price": (False, Numeric),
    "fill_qty": (False, Numeric),
    "slippage_bps": (True, Numeric),
    "fee_amount": (True, Numeric),
}


# (column, expected precision, expected scale)
PINNED_NUMERIC_PRECISION: list[tuple[str, int, int]] = [
    ("fill_price", 18, 8),
    ("fill_qty", 18, 8),
    ("fee_amount", 18, 8),
    ("slippage_bps", 10, 4),
]


def test_table_name_unchanged():
    assert PaperFill.__tablename__ == "paper_fills"


def test_business_column_set_unchanged():
    table_cols = set(PaperFill.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"PaperFill is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"PaperFill has unexpected new column(s): {sorted(extra)}. "
        "Adding columns to a fill-record table requires an explicit "
        "phase + ledger entry."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PaperFill.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PaperFill.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    # type(None) sentinel means "skip type assertion" (UUID FK)
    for col_name, (_n, expected_type) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is type(None):
            continue
        col = PaperFill.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"PaperFill.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_numeric_precision_unchanged():
    for col_name, expected_precision, expected_scale in PINNED_NUMERIC_PRECISION:
        col = PaperFill.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision, (
            f"PaperFill.{col_name} precision drifted: "
            f"expected {expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"PaperFill.{col_name} scale drifted: "
            f"expected {expected_scale}, got {col.type.scale}."
        )


def test_paper_order_id_fk_present_and_not_null():
    """Every fill MUST tie back to its order; otherwise orphan fills
    could silently appear and disrupt PnL/recon."""
    col = PaperFill.__table__.columns["paper_order_id"]
    fk_targets = {fk.target_fullname for fk in col.foreign_keys}
    assert "paper_orders.id" in fk_targets, (
        f"PaperFill.paper_order_id must keep FK -> paper_orders.id; "
        f"got {fk_targets}."
    )
    assert any(isinstance(fk, ForeignKey) for fk in col.foreign_keys)
    assert col.nullable is False, (
        "PaperFill.paper_order_id must remain NOT NULL — orphan fills "
        "are forbidden."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = PaperFill.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in PaperFill.__table__.primary_key.columns]
    assert pk_cols == ["id"]
