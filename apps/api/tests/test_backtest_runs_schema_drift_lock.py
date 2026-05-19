"""Cycle 49 — Schema drift-lock for ``backtest_runs``.

Strategy Lab backtest execution record. Populated by the offline
replay engine (MH-07+); never read or written by auto-trading code.

Pinned shape:
  * 11 business columns + nullability + String lengths
  * ``status`` indexed, default ``"queued"`` (anti-progression: a
    drift to "completed" or "running" would silently mark every
    new row as already-finished and bypass the worker)
  * ``starting_capital`` Numeric(20, 4) NOT NULL default 10000
    (Numeric(20,4) precision — drift to lower precision would
    truncate large-portfolio sims)
  * ``date_from`` and ``date_to`` are NOT-NULL timezone-aware
  * ``requested_assets`` / ``requested_timeframes`` /
    ``strategy_config_ids`` are NOT-NULL JSONB-family with empty
    dict default (anti-misfire: a NULL would let the worker run
    against the whole universe by accident)

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Numeric, String, Text

from app.db.models.backtest_run import BacktestRun


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "name": (False, String, 255),
    "status": (False, String, 50),
    "date_from": (False, DateTime, None),
    "date_to": (False, DateTime, None),
    "requested_assets": (False, None, None),  # JSONB
    "requested_timeframes": (False, None, None),  # JSONB
    "strategy_config_ids": (False, None, None),  # JSONB
    "starting_capital": (False, Numeric, None),
    "result_summary": (True, None, None),  # JSONB
    "error_message": (True, Text, None),
    "started_at": (True, DateTime, None),
    "completed_at": (True, DateTime, None),
}


JSONB_NOT_NULL_COLUMNS: list[str] = [
    "requested_assets", "requested_timeframes", "strategy_config_ids",
]
JSONB_NULLABLE_COLUMNS: list[str] = ["result_summary"]


def test_table_name_unchanged():
    assert BacktestRun.__tablename__ == "backtest_runs"


def test_business_column_set_unchanged():
    table_cols = set(BacktestRun.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"BacktestRun missing column(s): {sorted(missing)}."
    assert not extra, f"BacktestRun has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = BacktestRun.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"BacktestRun.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = BacktestRun.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_starting_capital_pinned_to_20_4():
    """Lower precision would truncate large-portfolio sims."""
    col = BacktestRun.__table__.columns["starting_capital"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 20
    assert col.type.scale == 4
    assert col.default is not None
    assert col.default.arg == 10000, (
        f"BacktestRun.starting_capital default drifted: got {col.default.arg!r}."
    )


def test_status_default_queued_and_indexed():
    """Anti-progression: a drift to 'completed'/'running' default would
    silently mark every new row as already-finished and bypass the worker."""
    col = BacktestRun.__table__.columns["status"]
    assert col.default is not None
    assert col.default.arg == "queued", (
        f"BacktestRun.status default drifted: got {col.default.arg!r}."
    )
    assert col.index is True, "BacktestRun.status must remain indexed."


def test_jsonb_not_null_columns_have_dict_default():
    """Anti-misfire: a NULL would let the worker run against the whole
    universe by accident."""
    for col_name in JSONB_NOT_NULL_COLUMNS:
        col = BacktestRun.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES
        assert col.nullable is False
        assert col.default is not None, (
            f"BacktestRun.{col_name} must keep a Python default to avoid NULL misfire."
        )
        # default.arg may be the dict callable
        default_value = col.default.arg
        if callable(default_value):
            default_value = default_value({})
        assert default_value == {}, (
            f"BacktestRun.{col_name} default drifted from empty dict; got {default_value!r}."
        )


def test_jsonb_nullable_columns_remain_jsonb_family():
    for col_name in JSONB_NULLABLE_COLUMNS:
        col = BacktestRun.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES


def test_date_columns_are_timezone_aware():
    for col_name in ("date_from", "date_to", "started_at", "completed_at"):
        col = BacktestRun.__table__.columns[col_name]
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True, (
            f"BacktestRun.{col_name} timezone flag drifted."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = BacktestRun.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in BacktestRun.__table__.primary_key.columns]
    assert pk_cols == ["id"]
