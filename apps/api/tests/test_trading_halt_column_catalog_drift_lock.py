"""MH-DRIFTLOCK-TRADING-HALT-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.trading_halt import TradingHalt

_EXPECTED: frozenset[str] = frozenset(
    {
        "created_at", "halt_type", "id", "metadata_json", "reason", "resolution_notes",
        "resolved_at", "resolved_by", "scope", "status", "trading_mode",
        "triggered_at", "triggered_by", "updated_at",
    }
)
_SAFETY: frozenset[str] = frozenset(
    {
        "id", "halt_type", "status", "scope", "trading_mode",
        "triggered_at", "triggered_by", "resolved_at",
    }
)


def test_trading_halt_full_column_catalog() -> None:
    actual = frozenset(c.name for c in TradingHalt.__table__.columns)
    assert actual == _EXPECTED, f"TradingHalt column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_trading_halt_safety_subset_present() -> None:
    actual = frozenset(c.name for c in TradingHalt.__table__.columns)
    missing = _SAFETY - actual
    assert not missing, f"TradingHalt safety subset missing: {sorted(missing)}"
    assert _SAFETY.issubset(_EXPECTED)
