"""MH-DRIFTLOCK-RISK-LIMIT-CONFIG-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.risk_limit_config import RiskLimitConfig

_EXPECTED: frozenset[str] = frozenset(
    {
        "created_at", "daily_loss_limit_amount", "daily_loss_limit_pct", "id", "is_active",
        "max_open_positions", "max_order_notional", "max_symbol_exposure", "max_total_exposure",
        "max_trades_per_day", "min_cash_buffer", "notes", "scope", "trading_mode", "updated_at",
    }
)
_SAFETY: frozenset[str] = frozenset(
    {
        "id", "scope", "trading_mode", "is_active",
        "max_order_notional", "max_total_exposure", "max_open_positions",
        "max_trades_per_day", "daily_loss_limit_amount",
    }
)


def test_risk_limit_config_full_column_catalog() -> None:
    actual = frozenset(c.name for c in RiskLimitConfig.__table__.columns)
    assert actual == _EXPECTED, f"RiskLimitConfig column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_risk_limit_config_safety_subset_present() -> None:
    actual = frozenset(c.name for c in RiskLimitConfig.__table__.columns)
    missing = _SAFETY - actual
    assert not missing, f"RiskLimitConfig safety subset missing: {sorted(missing)}"
    assert _SAFETY.issubset(_EXPECTED)
