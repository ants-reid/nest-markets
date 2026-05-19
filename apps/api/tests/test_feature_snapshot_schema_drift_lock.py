"""Cycle 38 — Schema drift-lock for ``feature_snapshots``.

FK target of ``signals.feature_snapshot_id``. Most important invariants:
the unique constraint on ``(asset_id, timeframe, scan_ts)`` (without it
duplicate snapshots could silently shadow each other) and the matching
composite index.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection only.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Enum, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.feature_snapshot import FeatureSnapshot


JSONB_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "asset_id": (False, UUID, None),
    "signal_id": (True, UUID, None),
    "scan_ts": (False, DateTime, None),
    "timeframe": (False, String, 10),
    "trend_score": (True, Numeric, None),
    "momentum_score": (True, Numeric, None),
    "volatility_score": (True, Numeric, None),
    "liquidity_score": (True, Numeric, None),
    "relative_strength_score": (True, Numeric, None),
    "regime": (True, Enum, None),
    "atr": (True, Numeric, None),
    "rsi": (True, Numeric, None),
    "ema_fast": (True, Numeric, None),
    "ema_slow": (True, Numeric, None),
    "adx": (True, Numeric, None),
    "distance_from_high_pct": (True, Numeric, None),
    "distance_from_low_pct": (True, Numeric, None),
    "market_quality_flag": (True, String, 50),
    "features_json": (True, type(None), None),  # JSONB-family
}


EXPECTED_NUMERIC_PRECISION: dict[str, tuple[int, int]] = {
    "trend_score": (10, 4),
    "momentum_score": (10, 4),
    "volatility_score": (10, 4),
    "liquidity_score": (10, 4),
    "relative_strength_score": (10, 4),
    "atr": (18, 8),
    "rsi": (10, 4),
    "ema_fast": (18, 8),
    "ema_slow": (18, 8),
    "adx": (10, 4),
    "distance_from_high_pct": (10, 4),
    "distance_from_low_pct": (10, 4),
}


EXPECTED_FOREIGN_KEYS: dict[str, tuple[str, str]] = {
    "asset_id": ("assets", "id"),
    "signal_id": ("signals", "id"),
}


def test_table_name_unchanged():
    assert FeatureSnapshot.__tablename__ == "feature_snapshots"


def test_business_column_set_unchanged():
    table_cols = set(FeatureSnapshot.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"FeatureSnapshot is missing column(s): {sorted(missing)}."
    assert not extra, f"FeatureSnapshot has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = FeatureSnapshot.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"FeatureSnapshot.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = FeatureSnapshot.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"FeatureSnapshot.{col_name} length drifted: expected "
            f"{expected_len}, got {col.type.length}."
        )


def test_numeric_precision_unchanged():
    for col_name, (expected_precision, expected_scale) in EXPECTED_NUMERIC_PRECISION.items():
        col = FeatureSnapshot.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision, (
            f"FeatureSnapshot.{col_name} precision drifted: expected "
            f"{expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"FeatureSnapshot.{col_name} scale drifted: expected "
            f"{expected_scale}, got {col.type.scale}."
        )


def test_features_json_is_jsonb_family():
    col = FeatureSnapshot.__table__.columns["features_json"]
    type_name = type(col.type).__name__
    assert type_name in JSONB_TYPE_NAMES


def test_foreign_keys_unchanged():
    for col_name, (expected_table, expected_col) in EXPECTED_FOREIGN_KEYS.items():
        col = FeatureSnapshot.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert fks
        targets = {(fk.column.table.name, fk.column.name) for fk in fks}
        assert (expected_table, expected_col) in targets, (
            f"FeatureSnapshot.{col_name} FK drifted: expected "
            f"({expected_table}, {expected_col}), got {targets}."
        )


def test_unique_constraint_present():
    """``uq_feature_snapshots_asset_timeframe_scan_ts`` must remain so
    duplicate snapshots can't silently shadow each other."""
    uniques = [
        c
        for c in FeatureSnapshot.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    by_name = {u.name: u for u in uniques}
    assert "uq_feature_snapshots_asset_timeframe_scan_ts" in by_name, (
        "FeatureSnapshot is missing UniqueConstraint "
        "``uq_feature_snapshots_asset_timeframe_scan_ts``."
    )
    cols = [c.name for c in by_name["uq_feature_snapshots_asset_timeframe_scan_ts"].columns]
    assert cols == ["asset_id", "timeframe", "scan_ts"], (
        f"UniqueConstraint columns drifted: expected "
        f"['asset_id', 'timeframe', 'scan_ts'], got {cols}."
    )


def test_composite_index_present():
    indexes_by_name = {idx.name: idx for idx in FeatureSnapshot.__table__.indexes}
    name = "ix_feature_snapshots_asset_timeframe_scan_ts"
    assert name in indexes_by_name, f"Index {name} is missing."
    cols = [c.name for c in indexes_by_name[name].columns]
    assert cols == ["asset_id", "timeframe", "scan_ts"], (
        f"Index {name} columns drifted: got {cols}."
    )


def test_id_and_created_at_supplied_by_mixins():
    cols = FeatureSnapshot.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in FeatureSnapshot.__table__.primary_key.columns]
    assert pk_cols == ["id"]
