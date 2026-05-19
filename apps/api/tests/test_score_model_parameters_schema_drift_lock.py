"""Cycle 46 — Schema drift-lock for ``score_model_parameters``.

Configurable scoring weights per model, bucket, and regime.

Pinned shape:
  * 10 business columns + nullability + String lengths
  * UNIQUE (model_registry_id, parameter_name, regime_tag) named
    ``uq_smp_model_param_regime`` — prevents two competing values
    for the same (model, parameter, regime) triple silently changing
    the active scoring weight
  * FK to score_model_registry.id ondelete=RESTRICT (you must NEVER
    be able to delete a model that still has parameters defined)
  * Numeric(18, 8) on parameter_value / min_value / max_value

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text

from app.db.models.score_model_parameters import ScoreModelParameters


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "model_registry_id": (False, None, None),  # UUID FK RESTRICT
    "parameter_name": (False, String, 255),
    "parameter_value": (True, Numeric, None),
    "min_value": (True, Numeric, None),
    "max_value": (True, Numeric, None),
    "parameter_type": (True, String, 50),
    "description": (True, Text, None),
    "regime_tag": (True, String, 100),
    "effective_date": (True, DateTime, None),
    "deprecated_at": (True, DateTime, None),
}


PINNED_NUMERIC_18_8: list[str] = ["parameter_value", "min_value", "max_value"]


def test_table_name_unchanged():
    assert ScoreModelParameters.__tablename__ == "score_model_parameters"


def test_business_column_set_unchanged():
    table_cols = set(ScoreModelParameters.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ScoreModelParameters missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ScoreModelParameters has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ScoreModelParameters.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ScoreModelParameters.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ScoreModelParameters.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_numeric_columns_pinned_to_18_8():
    for col_name in PINNED_NUMERIC_18_8:
        col = ScoreModelParameters.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 18
        assert col.type.scale == 8, (
            f"ScoreModelParameters.{col_name} scale drifted: "
            f"expected 8, got {col.type.scale}."
        )


def test_uq_model_param_regime_present():
    """Per (model, parameter, regime) UNIQUE — prevents two competing
    values silently changing the active scoring weight."""
    constraint_names = {
        c.name for c in ScoreModelParameters.__table__.constraints if c.name
    }
    assert "uq_smp_model_param_regime" in constraint_names, (
        "UNIQUE (model_registry_id, parameter_name, regime_tag) constraint missing."
    )


def test_model_fk_restrict():
    """ANTI-DESTRUCTION: FK to score_model_registry must remain
    RESTRICT — you must NEVER be able to delete a model that still
    has parameters defined."""
    col = ScoreModelParameters.__table__.columns["model_registry_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "score_model_registry.id"
    assert (fk.ondelete or "").upper() == "RESTRICT", (
        f"model_registry_id ondelete must remain RESTRICT; got {fk.ondelete!r}. "
        "ANTI-DESTRUCTION DRIFT."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ScoreModelParameters.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ScoreModelParameters.__table__.primary_key.columns]
    assert pk_cols == ["id"]
