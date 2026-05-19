"""Cycle 42 — Schema drift-lock for ``pnl_snapshots``.

Locks the portfolio equity / drawdown snapshot table — the dependency
surface for MH-COCKPIT-09 daily scoreboard and MH-157 performance
dimensions.

Pinned shape:
  * 10 business columns, full nullability map
  * Numeric precision: equity/cash/exposures/pnl=(18,8) — currency
    semantics; drawdown_pct/win_rate/profit_factor=(10,4) — ratio
    semantics
  * ``snapshot_ts`` indexed (the dominant query axis)
  * ``metadata_json`` JSONB-family

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Numeric

from app.db.models.pnl_snapshot import PnlSnapshot


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None]] = {
    "snapshot_ts": (False, DateTime),
    "equity": (True, Numeric),
    "cash": (True, Numeric),
    "gross_exposure": (True, Numeric),
    "net_exposure": (True, Numeric),
    "open_pnl": (True, Numeric),
    "closed_pnl": (True, Numeric),
    "drawdown_pct": (True, Numeric),
    "win_rate_rolling": (True, Numeric),
    "profit_factor_rolling": (True, Numeric),
    "metadata_json": (True, None),  # JSONB
}


# (column, expected precision, expected scale)
PINNED_NUMERIC_PRECISION: list[tuple[str, int, int]] = [
    ("equity", 18, 8),
    ("cash", 18, 8),
    ("gross_exposure", 18, 8),
    ("net_exposure", 18, 8),
    ("open_pnl", 18, 8),
    ("closed_pnl", 18, 8),
    ("drawdown_pct", 10, 4),
    ("win_rate_rolling", 10, 4),
    ("profit_factor_rolling", 10, 4),
]


def test_table_name_unchanged():
    assert PnlSnapshot.__tablename__ == "pnl_snapshots"


def test_business_column_set_unchanged():
    table_cols = set(PnlSnapshot.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"PnlSnapshot is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"PnlSnapshot has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PnlSnapshot.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PnlSnapshot.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = PnlSnapshot.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"PnlSnapshot.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_numeric_precision_unchanged():
    for col_name, expected_precision, expected_scale in PINNED_NUMERIC_PRECISION:
        col = PnlSnapshot.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision, (
            f"PnlSnapshot.{col_name} precision drifted: "
            f"expected {expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"PnlSnapshot.{col_name} scale drifted: "
            f"expected {expected_scale}, got {col.type.scale}."
        )


def test_metadata_json_is_jsonb_family():
    col = PnlSnapshot.__table__.columns["metadata_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES, (
        f"PnlSnapshot.metadata_json must remain a JSONB-family column; "
        f"got {type_name}."
    )


def test_snapshot_ts_is_indexed():
    """snapshot_ts is the dominant query axis (latest snapshot, range
    queries). Index drift here would silently degrade dashboard
    queries."""
    col = PnlSnapshot.__table__.columns["snapshot_ts"]
    assert col.index is True, (
        "PnlSnapshot.snapshot_ts must remain indexed (index=True)."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = PnlSnapshot.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in PnlSnapshot.__table__.primary_key.columns]
    assert pk_cols == ["id"]
