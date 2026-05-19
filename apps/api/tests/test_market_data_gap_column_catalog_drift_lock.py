"""MH-DRIFTLOCK-MARKET-DATA-GAP-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.market_data_gap import MarketDataGap

_EXPECTED: frozenset[str] = frozenset(
    {
        "asset_symbol", "created_at", "expected_candles_missing", "gap_end", "gap_start",
        "id", "import_run_id", "notes", "provider", "severity", "status", "timeframe",
    }
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "asset_symbol", "provider", "timeframe", "gap_start", "gap_end", "severity", "status"}
)


def test_market_data_gap_full_column_catalog() -> None:
    actual = frozenset(c.name for c in MarketDataGap.__table__.columns)
    assert actual == _EXPECTED, f"MarketDataGap column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_market_data_gap_safety_subset_present() -> None:
    actual = frozenset(c.name for c in MarketDataGap.__table__.columns)
    missing = _SAFETY - actual
    assert not missing, f"MarketDataGap safety subset missing: {sorted(missing)}"
    assert _SAFETY.issubset(_EXPECTED)
