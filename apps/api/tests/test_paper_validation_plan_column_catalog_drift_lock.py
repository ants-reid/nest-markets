"""MH-DRIFTLOCK-PAPER-VALIDATION-PLAN-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.paper_validation_plan import PaperValidationPlan

_EXPECTED: frozenset[str] = frozenset(
    {
        "backtest_metrics", "backtest_run_id", "baseline_candidate_id", "completed_at",
        "created_at", "created_by", "id", "max_daily_loss_pct", "max_drawdown_pct",
        "minimum_days", "paper_metrics", "pass_fail_reasons", "progress",
        "required_trades", "review_notes", "reviewed_by", "started_at",
        "starting_paper_capital", "status", "strategy_config_id", "target_profit_factor",
        "updated_at",
    }
)
_SAFETY: frozenset[str] = frozenset(
    {
        "id", "status", "strategy_config_id", "started_at", "completed_at",
        "max_daily_loss_pct", "max_drawdown_pct", "starting_paper_capital",
    }
)


def test_paper_validation_plan_full_column_catalog() -> None:
    actual = frozenset(c.name for c in PaperValidationPlan.__table__.columns)
    assert actual == _EXPECTED, f"PaperValidationPlan column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_paper_validation_plan_safety_subset_present() -> None:
    actual = frozenset(c.name for c in PaperValidationPlan.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
