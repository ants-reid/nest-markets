"""Cycle 40 — Schema drift-lock for ``trading_halts``.

Locks the durable trading-halt record. A halt row, when status='active',
indicates that trading is suspended for its scope.

Critical pinned defaults:
  * ``status`` defaults to ``'active'`` at both Python and server_default
    layers — a freshly-created halt row defaults to ACTIVE (i.e. halt
    is on). This is the SAFE direction for this table.
  * ``halt_type`` defaults to ``'manual'`` — a halt without an explicit
    type is treated as a manual operator-issued halt, not an automated
    one.
  * ``scope`` defaults to ``'global'`` — a halt without an explicit
    scope is treated as global, the WIDER (safer) interpretation.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import DateTime, String, Text

from app.db.models.trading_halt import TradingHalt


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "status": (False, String, 20),
    "halt_type": (False, String, 20),
    "scope": (False, String, 50),
    "trading_mode": (True, String, 20),
    "reason": (True, Text, None),
    "triggered_by": (True, String, 100),
    "triggered_at": (False, DateTime, None),
    "resolved_by": (True, String, 100),
    "resolved_at": (True, DateTime, None),
    "resolution_notes": (True, Text, None),
    "metadata_json": (True, None, None),  # JSON
}


# (column, expected python default, expected server_default substring lower-cased)
PINNED_DEFAULTS: list[tuple[str, str, str]] = [
    ("status", "active", "active"),
    ("halt_type", "manual", "manual"),
    ("scope", "global", "global"),
]


def test_table_name_unchanged():
    assert TradingHalt.__tablename__ == "trading_halts"


def test_business_column_set_unchanged():
    table_cols = set(TradingHalt.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"TradingHalt missing column(s): {sorted(missing)}."
    assert not extra, (
        f"TradingHalt has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = TradingHalt.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"TradingHalt.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = TradingHalt.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"TradingHalt.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = TradingHalt.__table__.columns[col_name]
        assert col.type.length == expected_len, (
            f"TradingHalt.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_metadata_json_is_json_family():
    col = TradingHalt.__table__.columns["metadata_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES, (
        f"TradingHalt.metadata_json must remain a JSON-family column; "
        f"got {type_name}."
    )


def test_pinned_string_defaults():
    """Pinned defaults — these affect halt-row interpretation:
      * status='active' (safe direction: a new halt is ON)
      * halt_type='manual' (operator-issued, not automated)
      * scope='global' (widest, safest scope)
    Any silent flip changes how an unspecified halt row is read.
    """
    for col_name, expected_python, expected_server_substr in PINNED_DEFAULTS:
        col = TradingHalt.__table__.columns[col_name]
        assert col.default is not None, (
            f"TradingHalt.{col_name} lost its Python default — "
            "schema-drift breach."
        )
        assert col.default.arg == expected_python, (
            f"TradingHalt.{col_name} Python default drifted: "
            f"expected {expected_python!r}, got {col.default.arg!r}."
        )
        assert col.server_default is not None
        server_default_value = col.server_default.arg
        if hasattr(server_default_value, "text"):
            server_default_value = server_default_value.text
        assert expected_server_substr in str(server_default_value).lower(), (
            f"TradingHalt.{col_name} server_default drifted: "
            f"expected substring {expected_server_substr!r}, "
            f"got {server_default_value!r}."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = TradingHalt.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in TradingHalt.__table__.primary_key.columns]
    assert pk_cols == ["id"]
