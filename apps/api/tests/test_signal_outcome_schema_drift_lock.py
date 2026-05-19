"""Cycle 41 — Schema drift-lock for ``signal_outcomes``.

Locks the per-trade outcome record — the AI-learning-input table that
is the dependency surface of MH-155 (Auto SignalOutcome on close).
With MH-155 not yet shipped (writer deferred), this table is the
contract that every future writer must respect additively.

Pinned shape:
  * 12 business columns, full nullability map
  * 5 Enum columns (setup_type, direction, horizon_label,
    catalyst_type, regime_at_entry)
  * 2 FKs: signal_id -> signals.id (NOT NULL, indexed),
           asset_id  -> assets.id  (NOT NULL)
  * Numeric precision pins:
      - entry_price / exit_price        = (18, 8) — currency
      - actual_pnl_pct / mae_pct / mfe_pct = (10, 6) — %
      - r_multiple                      = (10, 4) — ratio
  * predicted_direction_correct: nullable Boolean (NOT a default-True
    placeholder — outcomes must be explicitly computed, never
    silently optimistic)

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric

from app.db.models.signal_outcome import SignalOutcome


# (nullable, type)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None]] = {
    "signal_id": (False, None),  # UUID FK
    "asset_id": (False, None),  # UUID FK
    "setup_type": (True, Enum),
    "direction": (True, Enum),
    "horizon_label": (True, Enum),
    "catalyst_type": (True, Enum),
    "regime_at_entry": (True, Enum),
    "entry_price": (True, Numeric),
    "exit_price": (True, Numeric),
    "predicted_direction_correct": (True, Boolean),
    "actual_pnl_pct": (True, Numeric),
    "r_multiple": (True, Numeric),
    "mae_pct": (True, Numeric),
    "mfe_pct": (True, Numeric),
    "closed_at": (True, DateTime),
}


# (column, expected precision, expected scale)
PINNED_NUMERIC_PRECISION: list[tuple[str, int, int]] = [
    ("entry_price", 18, 8),
    ("exit_price", 18, 8),
    ("actual_pnl_pct", 10, 6),
    ("r_multiple", 10, 4),
    ("mae_pct", 10, 6),
    ("mfe_pct", 10, 6),
]


# Expected FK targets (column -> referenced "table.column")
EXPECTED_FOREIGN_KEYS: dict[str, str] = {
    "signal_id": "signals.id",
    "asset_id": "assets.id",
}


def test_table_name_unchanged():
    assert SignalOutcome.__tablename__ == "signal_outcomes"


def test_business_column_set_unchanged():
    table_cols = set(SignalOutcome.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"SignalOutcome is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"SignalOutcome has unexpected new column(s): {sorted(extra)}. "
        "Adding columns to the AI-learning-input table requires an "
        "explicit phase + ledger entry — MH-155 contract surface."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t) in EXPECTED_BUSINESS_COLUMNS.items():
        col = SignalOutcome.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"SignalOutcome.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = SignalOutcome.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"SignalOutcome.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_numeric_precision_unchanged():
    for col_name, expected_precision, expected_scale in PINNED_NUMERIC_PRECISION:
        col = SignalOutcome.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision, (
            f"SignalOutcome.{col_name} precision drifted: "
            f"expected {expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"SignalOutcome.{col_name} scale drifted: "
            f"expected {expected_scale}, got {col.type.scale}."
        )


def test_expected_foreign_keys_present():
    for col_name, expected_target in EXPECTED_FOREIGN_KEYS.items():
        col = SignalOutcome.__table__.columns[col_name]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert expected_target in fk_targets, (
            f"SignalOutcome.{col_name} must keep FK -> "
            f"{expected_target}; got {fk_targets}."
        )
        assert any(isinstance(fk, ForeignKey) for fk in col.foreign_keys)


def test_signal_id_is_indexed():
    """signal_id is indexed for the dominant query pattern (find
    outcome for a given signal). Index drift here would silently
    degrade MH-155 lookups."""
    col = SignalOutcome.__table__.columns["signal_id"]
    assert col.index is True, (
        "SignalOutcome.signal_id must remain indexed (index=True). "
        "Without it, MH-155 outcome-lookup queries would degrade."
    )


def test_predicted_direction_correct_has_no_default():
    """``predicted_direction_correct`` must remain nullable AND
    default-less. A default-True placeholder would create silent
    optimism in AI-training data. Outcomes must be explicitly
    computed, never assumed."""
    col = SignalOutcome.__table__.columns["predicted_direction_correct"]
    assert col.nullable is True
    assert col.default is None, (
        "SignalOutcome.predicted_direction_correct gained a Python "
        "default — this would seed AI training data with assumed "
        "outcomes. ANTI-FALSE-POSITIVE DRIFT."
    )
    assert col.server_default is None, (
        "SignalOutcome.predicted_direction_correct gained a "
        "server_default — same anti-false-positive concern."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = SignalOutcome.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in SignalOutcome.__table__.primary_key.columns]
    assert pk_cols == ["id"]
