"""Cycle 53 — Schema drift-lock for ``drawdown_periods``.

One identified underwater window inside a backtest run, written by the
replay engine (MH-07+).

Pinned shape:
  * 6 business columns (1 soft-FK UUID + 3 timestamps + 1 NOT-NULL Numeric +
    1 nullable Integer + 1 NOT-NULL Boolean).
  * ``backtest_run_id``: nullable=False UUID, indexed BUT no formal FK
    (soft reference — research/audit data must not be CASCADE-deleted
    when a backtest run is reaped). Cycle-49+ soft-reference pattern.
  * ``max_drawdown_pct`` Numeric(10, 4) NOT-NULL — drift in precision
    would silently corrupt the historical drawdown distribution.
  * ``recovered`` Boolean NOT-NULL default False — anti-misfire guard
    so a NULL is never treated as "recovered".

Drift-lock notes:
    * Pure additive test; no production code change.
    * Replay engine output is READ-ONLY for the trading path. The auto-
      trading gate ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.drawdown_period import DrawdownPeriod


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "backtest_run_id": (False, None, None),  # soft-FK UUID
    "start_time": (False, DateTime, None),
    "trough_time": (True, DateTime, None),
    "end_time": (True, DateTime, None),
    "max_drawdown_pct": (False, Numeric, None),
    "duration_candles": (True, Integer, None),
    "recovered": (False, Boolean, None),
}


def test_table_name_unchanged():
    assert DrawdownPeriod.__tablename__ == "drawdown_periods"


def test_business_column_set_unchanged():
    table_cols = set(DrawdownPeriod.__table__.columns.keys())
    # CreatedAtMixin only: subtract {id, created_at}
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"DrawdownPeriod missing column(s): {sorted(missing)}."
    assert not extra, (
        f"DrawdownPeriod has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = DrawdownPeriod.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"DrawdownPeriod.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_backtest_run_id_is_soft_reference():
    """Soft-reference pattern: indexed UUID with NO FK constraint.

    Research output must survive backtest_runs deletion (audit trail).
    """
    col = DrawdownPeriod.__table__.columns["backtest_run_id"]
    assert isinstance(col.type, UUID), (
        f"DrawdownPeriod.backtest_run_id type drifted: expected UUID, "
        f"got {type(col.type).__name__}."
    )
    assert col.index is True, (
        "DrawdownPeriod.backtest_run_id.index drifted: expected True. "
        "Soft references must remain indexed for query performance."
    )
    fks = list(col.foreign_keys)
    assert len(fks) == 0, (
        f"DrawdownPeriod.backtest_run_id FK count drifted: expected 0 "
        f"(soft reference), got {len(fks)}. Adding a hard FK risks "
        "CASCADE-deleting research/audit data."
    )


def test_max_drawdown_pct_precision_10_4_unchanged():
    col = DrawdownPeriod.__table__.columns["max_drawdown_pct"]
    assert isinstance(col.type, Numeric), (
        f"DrawdownPeriod.max_drawdown_pct type drifted: expected Numeric, "
        f"got {type(col.type).__name__}."
    )
    assert col.type.precision == 10
    assert col.type.scale == 4


def test_recovered_boolean_default_false_both_layers():
    """``recovered`` must default to False; drift could silently mark every
    new drawdown as "already recovered" in metric rollups."""
    col = DrawdownPeriod.__table__.columns["recovered"]
    assert isinstance(col.type, Boolean)
    assert col.default is not None, "DrawdownPeriod.recovered missing Python-side default."
    default_value = col.default.arg
    if callable(default_value):
        default_value = default_value({})
    assert default_value is False, (
        f"DrawdownPeriod.recovered default drifted: expected False, got {default_value!r}."
    )


def test_timestamps_are_timezone_aware():
    for col_name in ("start_time", "trough_time", "end_time"):
        col = DrawdownPeriod.__table__.columns[col_name]
        assert isinstance(col.type, DateTime), (
            f"DrawdownPeriod.{col_name} type drifted."
        )
        assert col.type.timezone is True, (
            f"DrawdownPeriod.{col_name}.timezone drifted: expected True."
        )
