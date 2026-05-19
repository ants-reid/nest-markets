"""Cycle 48 — Schema drift-lock for ``missed_opportunity_labels``.

Counterfactual labels for opportunities that were NOT executed.
Used by the learning loop to attribute opportunity cost.

Pinned shape:
  * 7 business columns + nullability + String lengths
  * 2 NOT-NULL CASCADE FKs:
      - opportunity_id → scored_opportunities.id CASCADE
      - signal_id → signals.id CASCADE
  * Numeric pins:
      - 2 price columns at (18, 8): hypothetical_entry / hypothetical_exit
      - 3 ratio columns at (10, 4): hypothetical_pnl_pct /
        hypothetical_drawdown / actual_market_move_pct

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Numeric, String

from app.db.models.missed_opportunity_labels import MissedOpportunityLabel


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "opportunity_id": (False, None, None),  # UUID FK CASCADE
    "signal_id": (False, None, None),  # UUID FK CASCADE
    "reason_not_executed": (True, String, 255),
    "hypothetical_entry": (True, Numeric, None),
    "hypothetical_exit": (True, Numeric, None),
    "hypothetical_pnl_pct": (True, Numeric, None),
    "hypothetical_drawdown": (True, Numeric, None),
    "actual_market_move_pct": (True, Numeric, None),
    "opportunity_value_label": (True, String, 100),
}


PINNED_NUMERIC_18_8: list[str] = ["hypothetical_entry", "hypothetical_exit"]


PINNED_NUMERIC_10_4: list[str] = [
    "hypothetical_pnl_pct",
    "hypothetical_drawdown",
    "actual_market_move_pct",
]


EXPECTED_FK_TARGETS: dict[str, str] = {
    "opportunity_id": "scored_opportunities.id",
    "signal_id": "signals.id",
}


def test_table_name_unchanged():
    assert MissedOpportunityLabel.__tablename__ == "missed_opportunity_labels"


def test_business_column_set_unchanged():
    table_cols = set(MissedOpportunityLabel.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"MissedOpportunityLabel missing column(s): {sorted(missing)}."
    assert not extra, (
        f"MissedOpportunityLabel has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MissedOpportunityLabel.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MissedOpportunityLabel.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = MissedOpportunityLabel.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_price_columns_pinned_to_18_8():
    for col_name in PINNED_NUMERIC_18_8:
        col = MissedOpportunityLabel.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 18
        assert col.type.scale == 8


def test_ratio_columns_pinned_to_10_4():
    for col_name in PINNED_NUMERIC_10_4:
        col = MissedOpportunityLabel.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 4


def test_fks_remain_cascade():
    for col_name, expected_target in EXPECTED_FK_TARGETS.items():
        col = MissedOpportunityLabel.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert isinstance(fk, ForeignKey)
        assert fk.target_fullname == expected_target
        assert (fk.ondelete or "").upper() == "CASCADE", (
            f"MissedOpportunityLabel.{col_name} FK ondelete must remain CASCADE."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = MissedOpportunityLabel.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in MissedOpportunityLabel.__table__.primary_key.columns]
    assert pk_cols == ["id"]
