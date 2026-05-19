"""Cycle 38 — Schema drift-lock for ``assets``.

Top-level FK target of ``signals.asset_id``, ``positions.asset_id``,
and ``feature_snapshots.asset_id``.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection only.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Enum, String

from app.db.models.asset import Asset


JSONB_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "symbol": (False, String, 50),
    "name": (True, String, 255),
    "asset_class": (False, Enum, None),
    "base_currency": (True, String, 20),
    "quote_currency": (True, String, 20),
    "exchange": (True, String, 100),
    "sector": (True, String, 100),
    "industry": (True, String, 100),
    "is_active": (False, Boolean, None),
    "metadata_json": (True, type(None), None),  # JSONB-family
    "ibkr_con_id": (True, BigInteger, None),
}


def test_table_name_unchanged():
    assert Asset.__tablename__ == "assets"


def test_business_column_set_unchanged():
    table_cols = set(Asset.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"Asset is missing column(s): {sorted(missing)}."
    assert not extra, f"Asset has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = Asset.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"Asset.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = Asset.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"Asset.{col_name} length drifted: expected {expected_len}, "
            f"got {col.type.length}."
        )


def test_metadata_json_is_jsonb_family():
    col = Asset.__table__.columns["metadata_json"]
    type_name = type(col.type).__name__
    assert type_name in JSONB_TYPE_NAMES, (
        f"Asset.metadata_json must remain JSONB-family (got {type_name!r})."
    )


def test_symbol_is_unique_and_indexed():
    col = Asset.__table__.columns["symbol"]
    assert col.unique is True, "Asset.symbol must remain UNIQUE."
    assert col.index is True, "Asset.symbol must remain indexed."


def test_ibkr_con_id_is_indexed():
    col = Asset.__table__.columns["ibkr_con_id"]
    assert col.index is True, "Asset.ibkr_con_id must remain indexed."


def test_is_active_default_true():
    """``Asset.is_active`` default must remain True so a freshly-seeded
    asset is immediately tradable for read paths."""
    col = Asset.__table__.columns["is_active"]
    assert col.default is not None
    assert col.default.arg is True, (
        f"Asset.is_active Python default drifted: expected True, "
        f"got {col.default.arg!r}."
    )
    assert col.server_default is not None
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "true" in str(server_default_value).lower(), (
        f"Asset.is_active server_default drifted: expected 'true', "
        f"got {server_default_value!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = Asset.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in Asset.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"
