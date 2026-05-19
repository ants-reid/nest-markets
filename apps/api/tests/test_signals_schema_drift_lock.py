"""Cycle 37 — Schema drift-lock for ``signals``.

The ``signals`` table is the FK target of three downstream audit/decision
tables already locked by earlier cycles (``risk_decisions``,
``broker_submit_decisions``, ``news_in_decision_log``). Drifting its
shape silently invalidates every one of those locks.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection only.
    * No imports of ``trading_control_service`` or ``BrokerService``.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.signal import Signal


# Ship state — column → (nullable, expected SQLAlchemy type class, optional length).
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "asset_id": (False, UUID, None),
    "feature_snapshot_id": (True, UUID, None),
    "prompt_version_id": (True, UUID, None),
    "model_version_id": (True, UUID, None),
    "provider_name": (True, String, 100),
    "scan_ts": (False, DateTime, None),
    "timeframe": (False, String, 10),
    "signal_status": (False, Enum, None),
    "direction": (False, Enum, None),
    "setup_type": (False, Enum, None),
    "regime": (True, Enum, None),
    "entry_min": (True, Numeric, None),
    "entry_max": (True, Numeric, None),
    "stop_price": (True, Numeric, None),
    "target_price": (True, Numeric, None),
    "confidence": (True, Numeric, None),
    "horizon_label": (True, Enum, None),
    "catalyst_type": (True, Enum, None),
    "catalyst_score": (True, Numeric, None),
    "catalyst_summary": (True, Text, None),
    "thesis": (True, Text, None),
    "invalidators_json": (True, type(None), None),  # JSONB-family
    "signal_score": (True, Numeric, None),
    "raw_llm_json": (True, type(None), None),  # JSONB-family
}


JSONB_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# Numeric precision/scale ship state.
EXPECTED_NUMERIC_PRECISION: dict[str, tuple[int, int]] = {
    "entry_min": (18, 8),
    "entry_max": (18, 8),
    "stop_price": (18, 8),
    "target_price": (18, 8),
    "confidence": (10, 4),
    "catalyst_score": (10, 4),
    "signal_score": (10, 4),
}


# FK target ship state — column → (target_table, target_column).
EXPECTED_FOREIGN_KEYS: dict[str, tuple[str, str]] = {
    "asset_id": ("assets", "id"),
    "feature_snapshot_id": ("feature_snapshots", "id"),
    "prompt_version_id": ("prompt_versions", "id"),
    "model_version_id": ("model_versions", "id"),
}


# ORM-declared indexes (table-level Index objects).
EXPECTED_ORM_INDEXES: dict[str, list[str]] = {
    "ix_signals_asset_scan_ts": ["asset_id", "scan_ts"],
    "ix_signals_status_scan_ts": ["signal_status", "scan_ts"],
}


# --------------------------------------------------------------------------- #


def test_table_name_unchanged():
    assert Signal.__tablename__ == "signals"


def test_business_column_set_unchanged():
    table_cols = set(Signal.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"Signal is missing column(s): {sorted(missing)}. If you "
        "intend to drop columns, ship a matrix phase + migration + "
        "ledger entry."
    )
    assert not extra, (
        f"Signal has unexpected new column(s): {sorted(extra)}. If "
        "you intend to add columns, ship a matrix phase + migration + "
        "ledger entry and update this test."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = Signal.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"Signal.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}. Schema drift — "
            "ship a matrix phase + migration + ledger entry."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = Signal.__table__.columns[col_name]
        assert isinstance(col.type, String), (
            f"Signal.{col_name} must be String (got {type(col.type).__name__})."
        )
        assert col.type.length == expected_len, (
            f"Signal.{col_name} length drifted: expected "
            f"{expected_len}, got {col.type.length}."
        )


def test_numeric_precision_unchanged():
    for col_name, (expected_precision, expected_scale) in EXPECTED_NUMERIC_PRECISION.items():
        col = Signal.__table__.columns[col_name]
        assert isinstance(col.type, Numeric), (
            f"Signal.{col_name} must be Numeric (got {type(col.type).__name__})."
        )
        assert col.type.precision == expected_precision, (
            f"Signal.{col_name} precision drifted: expected "
            f"{expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"Signal.{col_name} scale drifted: expected "
            f"{expected_scale}, got {col.type.scale}."
        )


def test_jsonb_columns_remain_jsonb_family():
    for col_name in ("invalidators_json", "raw_llm_json"):
        col = Signal.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSONB_TYPE_NAMES, (
            f"Signal.{col_name} must remain JSONB-family (got {type_name!r})."
        )


def test_foreign_keys_unchanged():
    for col_name, (expected_table, expected_col) in EXPECTED_FOREIGN_KEYS.items():
        col = Signal.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert fks, f"Signal.{col_name} must keep its FK to {expected_table}.{expected_col}."
        targets = {(fk.column.table.name, fk.column.name) for fk in fks}
        assert (expected_table, expected_col) in targets, (
            f"Signal.{col_name} FK drifted: expected "
            f"({expected_table}, {expected_col}), got {targets}."
        )


def test_orm_declared_indexes_unchanged():
    indexes_by_name = {idx.name: idx for idx in Signal.__table__.indexes}
    for expected_name, expected_cols in EXPECTED_ORM_INDEXES.items():
        assert expected_name in indexes_by_name, (
            f"Signal ORM-declared index {expected_name!r} is missing. "
            "Schema drift — ship a matrix phase + ledger entry."
        )
        actual_cols = [c.name for c in indexes_by_name[expected_name].columns]
        assert actual_cols == expected_cols, (
            f"Index {expected_name} columns drifted: expected "
            f"{expected_cols}, got {actual_cols}."
        )


def test_id_and_created_at_supplied_by_mixins():
    cols = Signal.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in Signal.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"
