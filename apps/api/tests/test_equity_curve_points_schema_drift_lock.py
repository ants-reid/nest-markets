"""Cycle 49 — Schema drift-lock for ``equity_curve_points``.

One snapshot of portfolio equity during a backtest run. Append-only
high-volume time-series; written by the offline replay engine.

Pinned shape:
  * 5 business columns + nullability
  * ``backtest_run_id`` is NOT-NULL UUID, **indexed**, soft-reference
    (no formal FK at ORM layer — locked so a future change can't
    introduce a CASCADE that would orphan an in-progress analysis).
  * ``timestamp`` is NOT-NULL timezone-aware AND indexed (composite
    range queries on the equity curve depend on this index).
  * ``equity`` is NOT-NULL Numeric(20, 4) (high precision required
    for large-portfolio simulations).
  * ``cash`` and ``open_pnl`` Numeric(20, 4).
  * ``drawdown_pct`` Numeric(10, **6**) — note the **6 fractional
    digits** (not the usual 4) because intraday drawdown values
    can be very small (single-basis-point precision needed).

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Numeric

from app.db.models.equity_curve_point import EquityCurvePoint


# (nullable, type)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None]] = {
    "backtest_run_id": (False, None),  # UUID indexed, NO FK
    "timestamp": (False, DateTime),
    "equity": (False, Numeric),
    "cash": (True, Numeric),
    "open_pnl": (True, Numeric),
    "drawdown_pct": (True, Numeric),
}


PINNED_NUMERIC_20_4: list[str] = ["equity", "cash", "open_pnl"]


def test_table_name_unchanged():
    assert EquityCurvePoint.__tablename__ == "equity_curve_points"


def test_business_column_set_unchanged():
    table_cols = set(EquityCurvePoint.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"EquityCurvePoint missing column(s): {sorted(missing)}."
    assert not extra, (
        f"EquityCurvePoint has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t) in EXPECTED_BUSINESS_COLUMNS.items():
        col = EquityCurvePoint.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"EquityCurvePoint.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_money_columns_pinned_to_20_4():
    """High precision required for large-portfolio simulations."""
    for col_name in PINNED_NUMERIC_20_4:
        col = EquityCurvePoint.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 20
        assert col.type.scale == 4, (
            f"EquityCurvePoint.{col_name} scale drifted: "
            f"expected 4, got {col.type.scale}."
        )


def test_drawdown_pct_pinned_to_10_6():
    """Single-basis-point precision needed for intraday drawdown."""
    col = EquityCurvePoint.__table__.columns["drawdown_pct"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 10
    assert col.type.scale == 6, (
        "EquityCurvePoint.drawdown_pct must remain Numeric(10, 6) — drift "
        "to (10, 4) would silently truncate intraday drawdown signals."
    )


def test_timestamp_is_timezone_aware_and_indexed():
    col = EquityCurvePoint.__table__.columns["timestamp"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True
    assert col.index is True, (
        "EquityCurvePoint.timestamp must remain indexed — equity-curve "
        "range queries depend on this index."
    )


def test_backtest_run_id_indexed_but_no_fk():
    """Locked: a future change must not introduce a CASCADE that would
    orphan an in-progress analysis."""
    col = EquityCurvePoint.__table__.columns["backtest_run_id"]
    assert col.index is True
    assert col.nullable is False
    assert len(list(col.foreign_keys)) == 0, (
        "EquityCurvePoint.backtest_run_id must remain a soft reference "
        "(no formal FK) so equity-curve points survive backtest reaping."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = EquityCurvePoint.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in EquityCurvePoint.__table__.primary_key.columns]
    assert pk_cols == ["id"]
