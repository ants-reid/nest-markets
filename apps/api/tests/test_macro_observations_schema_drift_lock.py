"""Cycle 47 — Schema drift-lock for ``macro_observations``.

Individual data points for a macroeconomic time series.

Pinned shape:
  * 4 business columns + nullability
  * UNIQUE (macro_series_id, observation_date) named
    ``uq_macro_obs_series_date`` — per-series/date dedupe; drift
    would silently maintain two competing observation values
  * Index ``ix_macro_obs_date``
  * NOT-NULL CASCADE FK macro_series_id → macro_series.id (deleting
    a series must cascade observations — orphan observations would
    silently reference a missing series)
  * NOT-NULL Numeric(24, 8) on observation_value (24 digits cover
    yields, indices, basis points, and absolute dollar series)
  * JSONB-family ``extra_metadata``

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Date, ForeignKey, Numeric

from app.db.models.macro_observations import MacroObservation


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "macro_series_id": (False, None, None),  # UUID FK CASCADE
    "observation_date": (False, Date, None),
    "observation_value": (False, Numeric, None),  # NOT NULL!
    "extra_metadata": (True, None, None),  # JSONB
}


def test_table_name_unchanged():
    assert MacroObservation.__tablename__ == "macro_observations"


def test_business_column_set_unchanged():
    table_cols = set(MacroObservation.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"MacroObservation missing column(s): {sorted(missing)}."
    assert not extra, (
        f"MacroObservation has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MacroObservation.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MacroObservation.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_observation_value_pinned_to_24_8():
    col = MacroObservation.__table__.columns["observation_value"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 24
    assert col.type.scale == 8


def test_series_fk_cascade():
    col = MacroObservation.__table__.columns["macro_series_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "macro_series.id"
    assert (fk.ondelete or "").upper() == "CASCADE"


def test_uq_series_date_present():
    constraint_names = {c.name for c in MacroObservation.__table__.constraints if c.name}
    assert "uq_macro_obs_series_date" in constraint_names, (
        "UNIQUE (macro_series_id, observation_date) constraint missing — "
        "would allow two competing observation values for the same series/date."
    )


def test_observation_date_index_present():
    indexes_by_name = {idx.name: idx for idx in MacroObservation.__table__.indexes}
    assert "ix_macro_obs_date" in indexes_by_name


def test_extra_metadata_is_jsonb_family():
    col = MacroObservation.__table__.columns["extra_metadata"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_id_and_timestamps_supplied_by_mixins():
    cols = MacroObservation.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in MacroObservation.__table__.primary_key.columns]
    assert pk_cols == ["id"]
