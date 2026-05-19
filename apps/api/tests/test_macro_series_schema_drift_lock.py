"""Cycle 47 — Schema drift-lock for ``macro_series``.

Metadata for macroeconomic data series (CPI, yields, VIX, etc.).

Pinned shape:
  * 6 business columns + nullability + String lengths
  * ``series_code`` is UNIQUE (per-series-code dedupe — drift would
    let two competing rows describe the same external series)
  * No defaults that could silently re-classify a series

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import String, Text

from app.db.models.macro_series import MacroSeries


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "series_code": (False, String, 100),
    "series_name": (False, String, 255),
    "description": (True, Text, None),
    "units": (True, String, 50),
    "frequency": (True, String, 20),
    "source": (True, String, 100),
}


def test_table_name_unchanged():
    assert MacroSeries.__tablename__ == "macro_series"


def test_business_column_set_unchanged():
    table_cols = set(MacroSeries.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"MacroSeries missing column(s): {sorted(missing)}."
    assert not extra, f"MacroSeries has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MacroSeries.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MacroSeries.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = MacroSeries.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_series_code_unique():
    """Per-series-code dedupe — drift would let two competing rows
    describe the same external series (e.g. two 'CPIAUCSL' entries
    pointing at different units/frequency)."""
    col = MacroSeries.__table__.columns["series_code"]
    assert col.unique is True, (
        "MacroSeries.series_code must remain UNIQUE — duplicate series "
        "codes would silently fork series identity."
    )


def test_no_defaults_on_business_columns():
    """No defaults — every series must be explicitly classified by the
    ingest pipeline. A silent default on units/frequency/source could
    silently misclassify external data."""
    for col_name in EXPECTED_BUSINESS_COLUMNS.keys():
        col = MacroSeries.__table__.columns[col_name]
        assert col.default is None, (
            f"MacroSeries.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"MacroSeries.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = MacroSeries.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in MacroSeries.__table__.primary_key.columns]
    assert pk_cols == ["id"]
