"""Cycle 51 — Schema drift-lock for ``strategy_configs``.

Persisted configuration for a Strategy Lab (research-stage) strategy.
Read-only for the trading path; consumed only by the offline
backtest engine.

Pinned shape:
  * 7 business columns + nullability + String lengths
  * ``asset`` and ``timeframe`` are NOT-NULL indexed identifiers
    (used by Strategy Lab dashboards; drift would silently slow
    every browse query).
  * Two NOT-NULL JSONB columns with empty-dict defaults
    (parameters / risk_settings) — anti-misfire so a NULL doesn't
    silently get treated as "no risk settings" when a backtest
    is launched.
  * ``enabled`` Boolean default ``True`` — note: this is the
    *research-stage* strategy enabled flag, NOT a live-trading
    flag. The pin here is **anti-mass-disable**: drift to False
    would silently turn off every newly-created research strategy
    and break the Strategy Lab onboarding flow.

Drift-lock notes:
    * Pure additive test; no production code change.
    * StrategyConfig.enabled is research-only; it does not gate
      auto-trading. assert_auto_trading_allowed() is the only
      auto-trading gate and is unchanged by this lock.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String

from app.db.models.strategy_config import StrategyConfig


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "name": (False, String, 255),
    "strategy_type": (False, String, 100),
    "asset": (False, String, 50),
    "timeframe": (False, String, 10),
    "parameters": (False, None, None),  # JSONB empty dict
    "risk_settings": (False, None, None),  # JSONB empty dict
    "enabled": (False, Boolean, None),
}


JSONB_NOT_NULL_DICT_COLUMNS: list[str] = ["parameters", "risk_settings"]


INDEXED_IDENTIFIER_COLUMNS: list[str] = ["asset", "timeframe"]


def test_table_name_unchanged():
    assert StrategyConfig.__tablename__ == "strategy_configs"


def test_business_column_set_unchanged():
    table_cols = set(StrategyConfig.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"StrategyConfig missing column(s): {sorted(missing)}."
    assert not extra, (
        f"StrategyConfig has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = StrategyConfig.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"StrategyConfig.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = StrategyConfig.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_identifier_columns_indexed():
    """Drift would silently slow every Strategy Lab browse query."""
    for col_name in INDEXED_IDENTIFIER_COLUMNS:
        col = StrategyConfig.__table__.columns[col_name]
        assert col.index is True


def test_jsonb_not_null_dict_default():
    """Anti-misfire so a NULL doesn't silently get treated as 'no risk
    settings' when a backtest is launched."""
    for col_name in JSONB_NOT_NULL_DICT_COLUMNS:
        col = StrategyConfig.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES
        assert col.nullable is False
        assert col.default is not None
        default_value = col.default.arg
        if callable(default_value):
            default_value = default_value({})
        assert default_value == {}, (
            f"StrategyConfig.{col_name} default drifted from empty dict; "
            f"got {default_value!r}."
        )


def test_enabled_default_true_research_only():
    """Anti-mass-disable: drift to False would silently turn off every
    newly-created research strategy and break Strategy Lab onboarding.
    This is RESEARCH-stage; not an auto-trading gate."""
    col = StrategyConfig.__table__.columns["enabled"]
    assert isinstance(col.type, Boolean)
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg is True, (
        f"StrategyConfig.enabled default drifted: got {col.default.arg!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = StrategyConfig.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in StrategyConfig.__table__.primary_key.columns]
    assert pk_cols == ["id"]
