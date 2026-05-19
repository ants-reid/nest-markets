"""Cycle 48 — Schema drift-lock for ``eval_runs``.

Evaluation run history — append-only audit of every benchmark execution.

Pinned shape:
  * 9 business columns + nullability + String lengths
  * 2 FKs (no explicit ondelete — defaults to NO ACTION):
      - prompt_version_id → prompt_versions.id
      - model_version_id → model_versions.id
    Both nullable so an eval run can target only one or the other.
  * Numeric(10, 4) on summary_score / pass_rate
  * Both timestamps timezone-aware
  * ``output_json`` JSONB-family

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric, String

from app.db.models.eval_run import EvalRun


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "prompt_version_id": (True, None, None),  # UUID FK (nullable)
    "model_version_id": (True, None, None),  # UUID FK (nullable)
    "provider_name": (True, String, 100),
    "started_at": (True, DateTime, None),
    "completed_at": (True, DateTime, None),
    "summary_score": (True, Numeric, None),
    "pass_rate": (True, Numeric, None),
    "output_json": (True, None, None),  # JSONB
    "notes": (True, String, 1000),
}


PINNED_NUMERIC_10_4: list[str] = ["summary_score", "pass_rate"]


EXPECTED_FK_TARGETS: dict[str, str] = {
    "prompt_version_id": "prompt_versions.id",
    "model_version_id": "model_versions.id",
}


def test_table_name_unchanged():
    assert EvalRun.__tablename__ == "eval_runs"


def test_business_column_set_unchanged():
    table_cols = set(EvalRun.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"EvalRun missing column(s): {sorted(missing)}."
    assert not extra, f"EvalRun has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = EvalRun.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"EvalRun.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = EvalRun.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_numeric_columns_pinned_to_10_4():
    for col_name in PINNED_NUMERIC_10_4:
        col = EvalRun.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 4


def test_fk_targets_unchanged():
    for col_name, expected_target in EXPECTED_FK_TARGETS.items():
        col = EvalRun.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert isinstance(fk, ForeignKey)
        assert fk.target_fullname == expected_target


def test_timestamps_are_timezone_aware():
    for col_name in ("started_at", "completed_at"):
        col = EvalRun.__table__.columns[col_name]
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True, (
            f"EvalRun.{col_name} timezone flag drifted — would silently "
            "store eval run times as naive datetimes."
        )


def test_output_json_is_jsonb_family():
    col = EvalRun.__table__.columns["output_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_id_and_timestamps_supplied_by_mixins():
    cols = EvalRun.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in EvalRun.__table__.primary_key.columns]
    assert pk_cols == ["id"]
