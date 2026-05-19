"""Cycle 47 — Schema drift-lock for ``fundamental_snapshots``.

Point-in-time fundamentals snapshot per asset.

Pinned shape:
  * 13 business columns + nullability
  * UNIQUE (asset_id, snapshot_date) named
    ``uq_fundamental_snapshots_asset_date`` — per-asset/date dedupe;
    drift would silently maintain two competing snapshots for the
    same date
  * NOT-NULL CASCADE FK asset_id → assets.id
  * Numeric pins: 10 ratio/margin cols at (18, 4); revenue/earnings
    at (24, 2) (large absolute dollars need extra digits)
  * JSONB-family ``extra_metadata``

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Date, ForeignKey, Numeric

from app.db.models.fundamental_snapshots import FundamentalSnapshot


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "asset_id": (False, None, None),  # UUID FK CASCADE
    "snapshot_date": (False, Date, None),
    "pe_ratio": (True, Numeric, None),
    "price_to_book": (True, Numeric, None),
    "debt_to_equity": (True, Numeric, None),
    "current_ratio": (True, Numeric, None),
    "roa": (True, Numeric, None),
    "roe": (True, Numeric, None),
    "gross_margin": (True, Numeric, None),
    "net_margin": (True, Numeric, None),
    "dividend_yield": (True, Numeric, None),
    "free_cash_flow": (True, Numeric, None),
    "revenue": (True, Numeric, None),
    "earnings": (True, Numeric, None),
    "extra_metadata": (True, None, None),  # JSONB
}


PINNED_NUMERIC_18_4: list[str] = [
    "pe_ratio", "price_to_book", "debt_to_equity", "current_ratio",
    "roa", "roe", "gross_margin", "net_margin", "dividend_yield",
    "free_cash_flow",
]


PINNED_NUMERIC_24_2: list[str] = ["revenue", "earnings"]


def test_table_name_unchanged():
    assert FundamentalSnapshot.__tablename__ == "fundamental_snapshots"


def test_business_column_set_unchanged():
    table_cols = set(FundamentalSnapshot.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"FundamentalSnapshot missing column(s): {sorted(missing)}."
    assert not extra, (
        f"FundamentalSnapshot has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = FundamentalSnapshot.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"FundamentalSnapshot.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_ratio_columns_pinned_to_18_4():
    for col_name in PINNED_NUMERIC_18_4:
        col = FundamentalSnapshot.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 18
        assert col.type.scale == 4, (
            f"FundamentalSnapshot.{col_name} scale drifted: "
            f"expected 4, got {col.type.scale}."
        )


def test_dollar_columns_pinned_to_24_2():
    """Revenue/earnings need extra digits for large-cap absolute dollars."""
    for col_name in PINNED_NUMERIC_24_2:
        col = FundamentalSnapshot.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 24
        assert col.type.scale == 2, (
            f"FundamentalSnapshot.{col_name} scale drifted: "
            f"expected 2, got {col.type.scale}."
        )


def test_asset_fk_cascade():
    col = FundamentalSnapshot.__table__.columns["asset_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "assets.id"
    assert (fk.ondelete or "").upper() == "CASCADE"


def test_uq_asset_date_present():
    """Per-asset/date dedupe; drift would silently maintain two
    competing snapshots for the same date."""
    constraint_names = {c.name for c in FundamentalSnapshot.__table__.constraints if c.name}
    assert "uq_fundamental_snapshots_asset_date" in constraint_names


def test_extra_metadata_is_jsonb_family():
    col = FundamentalSnapshot.__table__.columns["extra_metadata"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_id_and_timestamps_supplied_by_mixins():
    cols = FundamentalSnapshot.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in FundamentalSnapshot.__table__.primary_key.columns]
    assert pk_cols == ["id"]
