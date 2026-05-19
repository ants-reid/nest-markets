"""Cycle 48 — Schema drift-lock for ``scored_opportunities``.

Composite-scored signal ready for ranking — head of the
opportunity-tracking trio. Read-only for execution code.

Pinned shape:
  * 11 business columns + nullability + String lengths
  * 2 indexes: ``ix_scored_opp_signal_id``,
    ``ix_scored_opp_asset_scored_at`` (composite for time-series
    ranking lookup)
  * 3 FKs:
      - signal_id → signals.id CASCADE
      - asset_id → assets.id CASCADE
      - model_version_id → score_model_registry.id SET NULL
        (a model can be archived without erasing the historical
        score record — important for the learning loop)
  * NOT-NULL Numeric(10,4) on ``score`` (the composite score itself
    must always be present — a NULL score would silently exclude
    the opportunity from ranking but leave the row in place)
  * Numeric(10,4) on 3 forecast columns (expected_move_pct /
    expected_drawdown_pct / do_not_trade_probability)
  * NOT-NULL timezone-aware ``scored_at``
  * JSONB-family ``score_components``

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text

from app.db.models.scored_opportunities import ScoredOpportunity


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "signal_id": (False, None, None),  # UUID FK CASCADE
    "asset_id": (False, None, None),  # UUID FK CASCADE
    "score": (False, Numeric, None),  # NOT NULL!
    "score_components": (True, None, None),  # JSONB
    "model_version_id": (True, None, None),  # UUID FK SET NULL
    "regime_tag": (True, String, 100),
    "bucket_assignment": (True, String, 255),
    "explanation": (True, Text, None),
    "expected_move_pct": (True, Numeric, None),
    "expected_drawdown_pct": (True, Numeric, None),
    "do_not_trade_probability": (True, Numeric, None),
    "scored_at": (False, DateTime, None),
}


PINNED_NUMERIC_10_4: list[str] = [
    "score",
    "expected_move_pct",
    "expected_drawdown_pct",
    "do_not_trade_probability",
]


EXPECTED_FK_ONDELETE: dict[str, tuple[str, str]] = {
    "signal_id": ("signals.id", "CASCADE"),
    "asset_id": ("assets.id", "CASCADE"),
    "model_version_id": ("score_model_registry.id", "SET NULL"),
}


EXPECTED_INDEXES: list[str] = [
    "ix_scored_opp_signal_id",
    "ix_scored_opp_asset_scored_at",
]


def test_table_name_unchanged():
    assert ScoredOpportunity.__tablename__ == "scored_opportunities"


def test_business_column_set_unchanged():
    table_cols = set(ScoredOpportunity.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ScoredOpportunity missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ScoredOpportunity has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ScoredOpportunity.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ScoredOpportunity.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ScoredOpportunity.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_numeric_columns_pinned_to_10_4():
    for col_name in PINNED_NUMERIC_10_4:
        col = ScoredOpportunity.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 4, (
            f"ScoredOpportunity.{col_name} scale drifted: "
            f"expected 4, got {col.type.scale}."
        )


def test_score_is_not_nullable():
    """Anti-rank-bypass: a NULL score would silently exclude the
    opportunity from ranking but leave the row in place."""
    col = ScoredOpportunity.__table__.columns["score"]
    assert col.nullable is False, (
        "ScoredOpportunity.score must remain NOT NULL — a NULL score "
        "would silently exclude the opportunity from ranking."
    )


def test_score_components_is_jsonb_family():
    col = ScoredOpportunity.__table__.columns["score_components"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_expected_fk_ondelete():
    for col_name, (expected_target, expected_ondelete) in EXPECTED_FK_ONDELETE.items():
        col = ScoredOpportunity.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert len(fks) == 1, f"{col_name} must keep exactly one FK."
        fk = fks[0]
        assert isinstance(fk, ForeignKey)
        assert fk.target_fullname == expected_target, (
            f"ScoredOpportunity.{col_name} FK target drifted: got {fk.target_fullname!r}."
        )
        assert (fk.ondelete or "").upper() == expected_ondelete.upper(), (
            f"ScoredOpportunity.{col_name} FK ondelete drifted: "
            f"expected {expected_ondelete!r}, got {fk.ondelete!r}."
        )


def test_scored_at_is_timezone_aware():
    col = ScoredOpportunity.__table__.columns["scored_at"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True


def test_expected_indexes_present():
    indexes_by_name = {idx.name: idx for idx in ScoredOpportunity.__table__.indexes}
    for name in EXPECTED_INDEXES:
        assert name in indexes_by_name, f"Index {name} is missing."


def test_id_and_timestamps_supplied_by_mixins():
    cols = ScoredOpportunity.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ScoredOpportunity.__table__.primary_key.columns]
    assert pk_cols == ["id"]
