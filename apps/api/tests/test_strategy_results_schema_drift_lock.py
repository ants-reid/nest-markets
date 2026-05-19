"""Cycle 53 — Schema drift-lock for ``strategy_results``.

Aggregate performance metrics produced by the replay engine (MH-07+).

Pinned shape:
  * 16 business columns (2 soft-FK UUIDs + 2 nullable identifiers +
    11 numeric metrics + 1 nullable JSONB).
  * ``backtest_run_id``: NOT-NULL UUID, indexed, NO formal FK (soft
    reference — research/audit must survive backtest_runs deletion).
  * ``strategy_config_id``: nullable UUID, indexed, NO formal FK
    (soft reference; some replays run without a saved config).
  * ``total_trades``/``wins``/``losses``/``breakeven`` Integer NOT-NULL
    default 0 — anti-NULL guard so dashboards don't render gaps.
  * ``win_rate`` Numeric(10, 6) (high precision; ratio in [0, 1]).
  * ``metrics`` JSONB nullable (not empty-dict default — allowed to be
    absent for legacy rows).

Drift-lock notes:
    * Pure additive test; no production code change.
    * Strategy results are READ-ONLY for the trading path. The auto-
      trading gate ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.strategy_result import StrategyResult


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "backtest_run_id": (False, None, None),  # soft-FK UUID
    "strategy_config_id": (True, None, None),  # soft-FK UUID
    "asset": (True, String, 50),
    "timeframe": (True, String, 10),
    "total_trades": (False, Integer, None),
    "wins": (False, Integer, None),
    "losses": (False, Integer, None),
    "breakeven": (False, Integer, None),
    "win_rate": (True, Numeric, None),
    "average_win": (True, Numeric, None),
    "average_loss": (True, Numeric, None),
    "profit_factor": (True, Numeric, None),
    "expectancy": (True, Numeric, None),
    "total_return_pct": (True, Numeric, None),
    "max_drawdown_pct": (True, Numeric, None),
    "score": (True, Numeric, None),
    "metrics": (True, None, None),  # JSONB nullable
}


INTEGER_DEFAULT_ZERO_COLUMNS: list[str] = ["total_trades", "wins", "losses", "breakeven"]


def test_table_name_unchanged():
    assert StrategyResult.__tablename__ == "strategy_results"


def test_business_column_set_unchanged():
    table_cols = set(StrategyResult.__table__.columns.keys())
    # TimestampMixin: subtract {id, created_at, updated_at}
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"StrategyResult missing column(s): {sorted(missing)}."
    assert not extra, (
        f"StrategyResult has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = StrategyResult.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"StrategyResult.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_pinned():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String:
            continue
        col = StrategyResult.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"StrategyResult.{col_name} String length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_soft_fk_uuids_indexed_no_fk():
    for col_name in ("backtest_run_id", "strategy_config_id"):
        col = StrategyResult.__table__.columns[col_name]
        assert isinstance(col.type, UUID), (
            f"StrategyResult.{col_name} type drifted: expected UUID."
        )
        assert col.index is True, (
            f"StrategyResult.{col_name}.index drifted: expected True."
        )
        assert len(list(col.foreign_keys)) == 0, (
            f"StrategyResult.{col_name} unexpectedly has FK; "
            "soft-reference pattern requires no formal FK."
        )


def test_integer_counts_default_zero():
    for col_name in INTEGER_DEFAULT_ZERO_COLUMNS:
        col = StrategyResult.__table__.columns[col_name]
        assert isinstance(col.type, Integer)
        assert col.default is not None, (
            f"StrategyResult.{col_name} missing default."
        )
        default_value = col.default.arg
        if callable(default_value):
            default_value = default_value({})
        assert default_value == 0, (
            f"StrategyResult.{col_name} default drifted: expected 0, got {default_value!r}."
        )


def test_win_rate_precision_10_6_unchanged():
    """win_rate is a ratio; precision (10, 6) must hold."""
    col = StrategyResult.__table__.columns["win_rate"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 10
    assert col.type.scale == 6


def test_metrics_is_jsonb_family():
    col = StrategyResult.__table__.columns["metrics"]
    assert type(col.type).__name__ in JSON_TYPE_NAMES, (
        f"StrategyResult.metrics type drifted: got {type(col.type).__name__}, "
        f"expected one of {sorted(JSON_TYPE_NAMES)}."
    )
