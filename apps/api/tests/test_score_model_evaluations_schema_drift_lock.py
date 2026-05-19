"""Cycle 46 — Schema drift-lock for ``score_model_evaluations``.

Validation results from training pipeline runs.

Pinned shape:
  * 10 business columns + nullability + String lengths
  * UNIQUE (model_registry_id, evaluation_run_id, metric_name) named
    ``uq_sme_model_run_metric`` — prevents two competing values for
    the same (model, run, metric) triple
  * FK to score_model_registry.id ondelete=RESTRICT (you must NEVER
    be able to delete a model that has evaluation history)
  * Numeric(18, 8) on metric_value
  * JSONB-family ``metric_details``

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String

from app.db.models.score_model_evaluations import ScoreModelEvaluation


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "model_registry_id": (False, None, None),  # UUID FK RESTRICT
    "evaluation_run_id": (False, String, 255),
    "evaluation_date": (False, DateTime, None),
    "validation_strategy": (True, String, 100),
    "metric_name": (True, String, 100),
    "metric_value": (True, Numeric, None),
    "metric_details": (True, None, None),  # JSONB
    "passed_gates": (True, Boolean, None),
    "gate_failures": (True, None, None),  # ARRAY(String)
    "evaluated_by": (True, String, 255),
}


def test_table_name_unchanged():
    assert ScoreModelEvaluation.__tablename__ == "score_model_evaluations"


def test_business_column_set_unchanged():
    table_cols = set(ScoreModelEvaluation.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ScoreModelEvaluation missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ScoreModelEvaluation has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ScoreModelEvaluation.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ScoreModelEvaluation.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ScoreModelEvaluation.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_metric_value_numeric_18_8():
    col = ScoreModelEvaluation.__table__.columns["metric_value"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 18
    assert col.type.scale == 8


def test_metric_details_is_jsonb_family():
    col = ScoreModelEvaluation.__table__.columns["metric_details"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_uq_model_run_metric_present():
    constraint_names = {
        c.name for c in ScoreModelEvaluation.__table__.constraints if c.name
    }
    assert "uq_sme_model_run_metric" in constraint_names, (
        "UNIQUE (model_registry_id, evaluation_run_id, metric_name) constraint missing — "
        "would allow two competing values for the same (model, run, metric) triple."
    )


def test_model_fk_restrict():
    """ANTI-DESTRUCTION: FK to score_model_registry must remain
    RESTRICT — you must NEVER be able to delete a model that has
    evaluation history."""
    col = ScoreModelEvaluation.__table__.columns["model_registry_id"]
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
    cols = ScoreModelEvaluation.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ScoreModelEvaluation.__table__.primary_key.columns]
    assert pk_cols == ["id"]
