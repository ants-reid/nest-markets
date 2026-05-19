"""Cycle 48 — Schema drift-lock for ``opportunity_outcomes``.

Realized outcome labels for the learning loop. Append-only;
written by the outcome-attribution worker after exit.

Pinned shape:
  * 14 business columns + nullability + String lengths
  * Index ``ix_opp_outcomes_opportunity_id``
  * 2 NOT-NULL CASCADE FKs:
      - opportunity_id → scored_opportunities.id CASCADE
      - signal_id → signals.id CASCADE
  * ``execution_status`` non-null Enum (EXECUTED/BLOCKED/MISSED/SKIPPED)
  * Numeric pins:
      - 3 price/PnL columns at (18, 8): entry_price/exit_price/realized_pnl
      - 7 ratio/score columns at (10, 4): realized_pnl_pct/expected_pnl_pct/
        slippage_pct/mfe_pct/mae_pct/r_multiple/execution_quality_score
  * NOT-NULL timezone-aware ``outcome_timestamp``

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric, String

from app.db.models.opportunity_outcomes import OpportunityOutcome


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "opportunity_id": (False, None, None),  # UUID FK CASCADE
    "signal_id": (False, None, None),  # UUID FK CASCADE
    "execution_status": (False, None, None),  # Enum
    "outcome_category": (True, String, 100),
    "entry_price": (True, Numeric, None),
    "exit_price": (True, Numeric, None),
    "realized_pnl": (True, Numeric, None),
    "realized_pnl_pct": (True, Numeric, None),
    "expected_pnl_pct": (True, Numeric, None),
    "slippage_pct": (True, Numeric, None),
    "mfe_pct": (True, Numeric, None),
    "mae_pct": (True, Numeric, None),
    "r_multiple": (True, Numeric, None),
    "exit_reason": (True, String, 100),
    "execution_quality_score": (True, Numeric, None),
    "outcome_timestamp": (False, DateTime, None),
}


PINNED_NUMERIC_18_8: list[str] = ["entry_price", "exit_price", "realized_pnl"]


PINNED_NUMERIC_10_4: list[str] = [
    "realized_pnl_pct", "expected_pnl_pct", "slippage_pct",
    "mfe_pct", "mae_pct", "r_multiple", "execution_quality_score",
]


EXPECTED_FK_TARGETS: dict[str, str] = {
    "opportunity_id": "scored_opportunities.id",
    "signal_id": "signals.id",
}


def test_table_name_unchanged():
    assert OpportunityOutcome.__tablename__ == "opportunity_outcomes"


def test_business_column_set_unchanged():
    table_cols = set(OpportunityOutcome.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"OpportunityOutcome missing column(s): {sorted(missing)}."
    assert not extra, (
        f"OpportunityOutcome has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = OpportunityOutcome.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"OpportunityOutcome.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = OpportunityOutcome.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_price_columns_pinned_to_18_8():
    for col_name in PINNED_NUMERIC_18_8:
        col = OpportunityOutcome.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 18
        assert col.type.scale == 8


def test_ratio_columns_pinned_to_10_4():
    for col_name in PINNED_NUMERIC_10_4:
        col = OpportunityOutcome.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 4


def test_fks_remain_cascade():
    for col_name, expected_target in EXPECTED_FK_TARGETS.items():
        col = OpportunityOutcome.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert isinstance(fk, ForeignKey)
        assert fk.target_fullname == expected_target
        assert (fk.ondelete or "").upper() == "CASCADE", (
            f"OpportunityOutcome.{col_name} FK ondelete must remain CASCADE; "
            f"got {fk.ondelete!r}."
        )


def test_outcome_timestamp_is_timezone_aware():
    col = OpportunityOutcome.__table__.columns["outcome_timestamp"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True


def test_opportunity_index_present():
    indexes_by_name = {idx.name: idx for idx in OpportunityOutcome.__table__.indexes}
    assert "ix_opp_outcomes_opportunity_id" in indexes_by_name


def test_id_and_timestamps_supplied_by_mixins():
    cols = OpportunityOutcome.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in OpportunityOutcome.__table__.primary_key.columns]
    assert pk_cols == ["id"]
