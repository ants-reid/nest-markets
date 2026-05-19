"""Cycle 50 — Schema drift-lock for ``feature_definitions``.

Registry of feature definitions with PIT-safety and normalization rules.
Read-only metadata table.

Pinned shape:
  * 11 business columns + nullability + String lengths
  * ``feature_name`` is UNIQUE — drift would allow two feature
    definitions to share a name and silently diverge in
    downstream feature lookups.
  * ``source_data_types`` is a Postgres ARRAY(String) (locked
    here so a future commit can't quietly demote it to JSONB
    or plain Text and break ARRAY-membership queries).
  * ``pit_safe`` Boolean **nullable with NO default** — locked
    intentionally so a feature must be explicitly tagged as
    PIT-safe or not; a default of True would silently mark
    unaudited features as point-in-time-safe and corrupt the
    learning-loop attribution.
  * ``default_value`` Numeric(18, 8).

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY

from app.db.models.feature_definitions import FeatureDefinition


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "feature_name": (False, String, 255),
    "feature_category": (True, String, 100),
    "description": (True, Text, None),
    "computation_rule": (True, Text, None),
    "source_data_types": (True, None, None),  # ARRAY(String)
    "pit_safe": (True, Boolean, None),
    "lookback_bars": (True, Integer, None),
    "default_value": (True, Numeric, None),
    "normalization_rule": (True, String, 255),
    "na_handling": (True, String, 100),
    "created_by": (True, String, 255),
}


def test_table_name_unchanged():
    assert FeatureDefinition.__tablename__ == "feature_definitions"


def test_business_column_set_unchanged():
    table_cols = set(FeatureDefinition.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"FeatureDefinition missing column(s): {sorted(missing)}."
    assert not extra, (
        f"FeatureDefinition has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = FeatureDefinition.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"FeatureDefinition.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = FeatureDefinition.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_feature_name_unique():
    """Drift would allow two feature definitions to share a name and
    silently diverge in downstream feature lookups."""
    col = FeatureDefinition.__table__.columns["feature_name"]
    assert col.unique is True


def test_source_data_types_is_postgres_array():
    """Locked: a future commit must not quietly demote this to JSONB
    or plain Text and break ARRAY-membership queries."""
    col = FeatureDefinition.__table__.columns["source_data_types"]
    assert isinstance(col.type, ARRAY), (
        f"FeatureDefinition.source_data_types must remain ARRAY; "
        f"got {type(col.type).__name__}."
    )


def test_pit_safe_has_no_default():
    """Anti-silent-PIT-claim: a default of True would silently mark
    unaudited features as point-in-time-safe and corrupt learning-loop
    attribution. A default of False would silently mask features that
    actually are PIT-safe."""
    col = FeatureDefinition.__table__.columns["pit_safe"]
    assert col.default is None, (
        "FeatureDefinition.pit_safe must remain default-less — every "
        "feature must be explicitly tagged."
    )
    assert col.server_default is None, (
        "FeatureDefinition.pit_safe must not have a server-side default."
    )


def test_default_value_pinned_to_18_8():
    col = FeatureDefinition.__table__.columns["default_value"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 18
    assert col.type.scale == 8


def test_id_and_timestamps_supplied_by_mixins():
    cols = FeatureDefinition.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in FeatureDefinition.__table__.primary_key.columns]
    assert pk_cols == ["id"]
