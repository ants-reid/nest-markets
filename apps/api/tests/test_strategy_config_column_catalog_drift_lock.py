"""MH-DRIFTLOCK-STRATEGY-CONFIG-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.strategy_config import StrategyConfig

_EXPECTED: frozenset[str] = frozenset(
    {"asset", "created_at", "enabled", "id", "name", "parameters",
     "risk_settings", "strategy_type", "timeframe", "updated_at"}
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "name", "asset", "timeframe", "strategy_type", "enabled", "risk_settings"}
)


def test_strategy_config_full_column_catalog() -> None:
    actual = frozenset(c.name for c in StrategyConfig.__table__.columns)
    assert actual == _EXPECTED, f"StrategyConfig column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_strategy_config_safety_subset_present() -> None:
    actual = frozenset(c.name for c in StrategyConfig.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
