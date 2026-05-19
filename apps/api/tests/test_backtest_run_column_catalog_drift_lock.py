"""MH-DRIFTLOCK-BACKTEST-RUN-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.backtest_run import BacktestRun

_EXPECTED: frozenset[str] = frozenset(
    {
        "completed_at", "created_at", "date_from", "date_to", "error_message", "id",
        "name", "requested_assets", "requested_timeframes", "result_summary",
        "started_at", "starting_capital", "status", "strategy_config_ids", "updated_at",
    }
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "status", "started_at", "completed_at", "starting_capital", "date_from", "date_to"}
)


def test_backtest_run_full_column_catalog() -> None:
    actual = frozenset(c.name for c in BacktestRun.__table__.columns)
    assert actual == _EXPECTED, f"BacktestRun column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_backtest_run_safety_subset_present() -> None:
    actual = frozenset(c.name for c in BacktestRun.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
