"""MH-DRIFTLOCK-BASELINE-CANDIDATE-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.baseline_candidate import BaselineCandidate

_EXPECTED: frozenset[str] = frozenset(
    {"ai_backtest_report_id", "asset", "backtest_run_id", "created_at", "created_by",
     "id", "metrics", "parameters", "review_notes", "reviewed_at", "reviewed_by",
     "status", "strategy_config_id", "strategy_type", "timeframe", "updated_at"}
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "asset", "timeframe", "strategy_type", "status",
     "strategy_config_id", "backtest_run_id", "reviewed_by"}
)


def test_baseline_candidate_full_column_catalog() -> None:
    actual = frozenset(c.name for c in BaselineCandidate.__table__.columns)
    assert actual == _EXPECTED, f"BaselineCandidate column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_baseline_candidate_safety_subset_present() -> None:
    actual = frozenset(c.name for c in BaselineCandidate.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
