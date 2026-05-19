"""Cycle 48 — Schema drift-lock for ``eval_cases``.

Evaluation benchmark cases for prompt + model regression testing.

Pinned shape:
  * 6 business columns + nullability + String lengths
  * ``name`` is UNIQUE (per-name dedupe — drift would let two
    competing benchmark cases share the same name and silently
    diverge in the dashboards)
  * ``category`` is NOT NULL
  * ``input_json`` is NOT NULL JSONB-family
  * ``expected_json`` and ``scoring_rules_json`` are JSONB-family
  * ``is_active`` defaults to ``True`` at BOTH Python and
    server_default layers — a flip to False would silently retire
    every newly-added benchmark.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import String

from app.db.models.eval_case import EvalCase


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "name": (False, String, 255),
    "category": (False, String, 100),
    "input_json": (False, None, None),  # JSONB NOT NULL
    "expected_json": (True, None, None),  # JSONB
    "scoring_rules_json": (True, None, None),  # JSONB
    "is_active": (False, None, None),  # Boolean
}


JSONB_COLUMNS: list[str] = ["input_json", "expected_json", "scoring_rules_json"]


def test_table_name_unchanged():
    assert EvalCase.__tablename__ == "eval_cases"


def test_business_column_set_unchanged():
    table_cols = set(EvalCase.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"EvalCase missing column(s): {sorted(missing)}."
    assert not extra, f"EvalCase has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = EvalCase.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"EvalCase.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = EvalCase.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_name_unique():
    """Per-name dedupe — drift would let two competing benchmark cases
    share the same name and silently diverge in dashboards."""
    col = EvalCase.__table__.columns["name"]
    assert col.unique is True, (
        "EvalCase.name must remain UNIQUE — duplicate names would silently "
        "diverge benchmark scoring."
    )


def test_jsonb_columns_remain_jsonb_family():
    for col_name in JSONB_COLUMNS:
        col = EvalCase.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES


def test_is_active_default_true_both_layers():
    """A flip to False would silently retire every newly-added benchmark."""
    col = EvalCase.__table__.columns["is_active"]
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg is True, (
        f"EvalCase.is_active Python default drifted: "
        f"expected True, got {col.default.arg!r}."
    )
    assert col.server_default is not None
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "true" in str(server_default_value).lower(), (
        f"EvalCase.is_active server_default drifted: got {server_default_value!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = EvalCase.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in EvalCase.__table__.primary_key.columns]
    assert pk_cols == ["id"]
