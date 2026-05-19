"""Cycle 45 — Schema drift-lock for ``paper_recommendations``.

Locks the recommendation-draft table (Bucket-4 dependency surface).

Pinned shape:
  * 18 business columns + nullability + String lengths
  * 3 indexes: signal, model, (status, created_at) composite
  * FKs: signal_id → signals.id, model_version_id → model_versions.id
  * Numeric pins: quantity / limit_price / estimated_notional = (18,8);
    confidence / risk_score = (10, 4)
  * **ANTI-ESCALATION**: ``status`` defaults to ``'draft'`` (Python).
    A fresh recommendation row must NEVER default to 'approved'/
    'executed' — that would let a write be silently auto-approved
    bypassing operator review.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text

from app.db.models.paper_recommendation import PaperRecommendation


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "signal_id": (True, None, None),  # UUID FK
    "model_version_id": (True, None, None),  # UUID FK
    "ticker": (False, String, 20),
    "side": (False, String, 20),
    "quantity": (False, Numeric, None),
    "order_type": (False, String, 50),
    "limit_price": (True, Numeric, None),
    "confidence": (True, Numeric, None),
    "risk_score": (True, Numeric, None),
    "estimated_notional": (True, Numeric, None),
    "rationale": (True, Text, None),
    "status": (False, String, 50),
    "reviewed_at": (True, DateTime, None),
    "reviewed_by": (True, String, 100),
    "review_notes": (True, Text, None),
    "executed_at": (True, DateTime, None),
    "paper_order_ids": (True, None, None),  # JSONB
    "source_metadata": (True, None, None),  # JSONB
}


PINNED_NUMERIC: list[tuple[str, int, int]] = [
    ("quantity", 18, 8),
    ("limit_price", 18, 8),
    ("estimated_notional", 18, 8),
    ("confidence", 10, 4),
    ("risk_score", 10, 4),
]


EXPECTED_FOREIGN_KEYS: dict[str, str] = {
    "signal_id": "signals.id",
    "model_version_id": "model_versions.id",
}


EXPECTED_INDEXES: list[str] = [
    "ix_paper_recommendations_signal",
    "ix_paper_recommendations_model",
    "ix_paper_recommendations_status_ts",
]


def test_table_name_unchanged():
    assert PaperRecommendation.__tablename__ == "paper_recommendations"


def test_business_column_set_unchanged():
    table_cols = set(PaperRecommendation.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"PaperRecommendation missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"PaperRecommendation has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PaperRecommendation.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PaperRecommendation.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = PaperRecommendation.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"PaperRecommendation.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_precision_unchanged():
    for col_name, expected_precision, expected_scale in PINNED_NUMERIC:
        col = PaperRecommendation.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision, (
            f"PaperRecommendation.{col_name} precision drifted: "
            f"expected {expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"PaperRecommendation.{col_name} scale drifted: "
            f"expected {expected_scale}, got {col.type.scale}."
        )


def test_jsonb_columns_remain_jsonb_family():
    for col_name in ("paper_order_ids", "source_metadata"):
        col = PaperRecommendation.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES, (
            f"PaperRecommendation.{col_name} must remain JSONB-family; "
            f"got {type_name}."
        )


def test_expected_foreign_keys_present():
    for col_name, expected_target in EXPECTED_FOREIGN_KEYS.items():
        col = PaperRecommendation.__table__.columns[col_name]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert expected_target in fk_targets, (
            f"PaperRecommendation.{col_name} must keep FK -> "
            f"{expected_target}; got {fk_targets}."
        )
        assert any(isinstance(fk, ForeignKey) for fk in col.foreign_keys)


def test_expected_indexes_present():
    indexes_by_name = {idx.name: idx for idx in PaperRecommendation.__table__.indexes}
    for name in EXPECTED_INDEXES:
        assert name in indexes_by_name, f"Index {name} is missing."


def test_status_anti_escalation_default():
    """ANTI-ESCALATION: a fresh recommendation row must default to
    ``status='draft'``. A silent flip to 'approved'/'executed' would
    let a write be auto-approved bypassing operator review."""
    col = PaperRecommendation.__table__.columns["status"]
    assert col.nullable is False
    assert col.default is not None, (
        "PaperRecommendation.status lost its Python default — "
        "ANTI-ESCALATION DRIFT."
    )
    default_value = col.default.arg
    # The model uses PaperRecommendationStatus.DRAFT (an Enum member);
    # accept either the enum member or its raw 'draft' value.
    default_str = getattr(default_value, "value", default_value)
    assert default_str == "draft", (
        f"PaperRecommendation.status default drifted: expected 'draft', "
        f"got {default_value!r} (resolved={default_str!r}). "
        "ANTI-ESCALATION DRIFT — a fresh recommendation must NEVER default "
        "to 'approved' or 'executed'."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = PaperRecommendation.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in PaperRecommendation.__table__.primary_key.columns]
    assert pk_cols == ["id"]
