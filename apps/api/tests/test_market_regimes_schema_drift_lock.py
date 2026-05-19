"""Cycle 50 — Schema drift-lock for ``market_regimes``.

Classification of market condition for a specific time window.
Read-only for the trading path; consumed by the regime-aware
scoring layer.

Pinned shape:
  * 9 business columns + nullability + String lengths
  * UNIQUE constraint ``uq_market_regimes_name_start`` on
    (regime_name, start_date) — drift would let two regime rows
    share the same (name, start) and silently double-count a
    regime in lookups.
  * Index ``ix_market_regimes_start_date`` on start_date.
  * ``regime_type`` is a NOT-NULL Enum with the named PG type
    ``market_regime_type_enum`` and a pinned 6-member value set
    (RISK_ON / RISK_OFF / HIGH_VOL / LOW_VOL / CHOP / TREND) —
    drift here would corrupt the regime lookup taxonomy.
  * ``volatility_percentile`` is Numeric(10, 4).
  * ``start_date`` NOT NULL Date; ``end_date`` nullable Date
    (nullable on purpose: the current regime has no end_date).

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Date, Enum as SAEnum, Numeric, String, Text

from app.db.enums import MarketRegimeType
from app.db.models.market_regimes import MarketRegime


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "regime_name": (False, String, 100),
    "regime_description": (True, Text, None),
    "start_date": (False, Date, None),
    "end_date": (True, Date, None),
    "characteristics": (True, None, None),  # JSONB
    "volatility_percentile": (True, Numeric, None),
    "trend_direction": (True, String, 50),
    "liquidity_condition": (True, String, 50),
    "regime_type": (False, None, None),  # Enum
}


EXPECTED_REGIME_TYPE_VALUES: frozenset[str] = frozenset({
    "risk_on", "risk_off", "high_vol", "low_vol", "chop", "trend",
})


def test_table_name_unchanged():
    assert MarketRegime.__tablename__ == "market_regimes"


def test_business_column_set_unchanged():
    table_cols = set(MarketRegime.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"MarketRegime missing column(s): {sorted(missing)}."
    assert not extra, f"MarketRegime has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MarketRegime.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MarketRegime.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = MarketRegime.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_volatility_percentile_pinned_to_10_4():
    col = MarketRegime.__table__.columns["volatility_percentile"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 10
    assert col.type.scale == 4


def test_characteristics_is_jsonb_family():
    col = MarketRegime.__table__.columns["characteristics"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_regime_type_enum_pinned():
    """Drift in this taxonomy would corrupt the regime lookup."""
    col = MarketRegime.__table__.columns["regime_type"]
    assert col.nullable is False
    assert isinstance(col.type, SAEnum)
    assert col.type.name == "market_regime_type_enum", (
        f"PG enum name drifted: got {col.type.name!r}."
    )
    actual_values = {m.value for m in MarketRegimeType}
    assert actual_values == EXPECTED_REGIME_TYPE_VALUES, (
        f"MarketRegimeType members drifted: expected {sorted(EXPECTED_REGIME_TYPE_VALUES)}, "
        f"got {sorted(actual_values)}."
    )


def test_unique_name_start_constraint_present():
    """Drift would let two regime rows share (name, start) and silently
    double-count a regime in lookups."""
    uqs = [
        c for c in MarketRegime.__table__.constraints
        if type(c).__name__ == "UniqueConstraint"
    ]
    names = {uq.name for uq in uqs}
    assert "uq_market_regimes_name_start" in names, (
        f"UNIQUE uq_market_regimes_name_start missing; got {sorted(names)}."
    )


def test_start_date_index_present():
    indexes_by_name = {idx.name: idx for idx in MarketRegime.__table__.indexes}
    assert "ix_market_regimes_start_date" in indexes_by_name


def test_id_and_timestamps_supplied_by_mixins():
    cols = MarketRegime.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in MarketRegime.__table__.primary_key.columns]
    assert pk_cols == ["id"]
