"""Tests for MH-143-A — position sizing service (additive only)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.position_sizing_service import (
    PositionSizingError,
    calculate_position_size,
)


def test_long_basic_risk_binding():
    # equity=100k, risk=1% -> $1000 risk; per-share risk=$5 -> 200 shares.
    r = calculate_position_size(
        equity="100000",
        risk_fraction="0.01",
        entry_price="100",
        stop_price="95",
        direction="long",
    )
    assert r.qty == Decimal("200")
    assert r.risk_dollars == Decimal("1000.00")
    assert r.per_share_risk == Decimal("5")
    assert r.notional == Decimal("20000")
    assert r.binding_cap == "risk"


def test_short_basic_risk_binding():
    r = calculate_position_size(
        equity="50000",
        risk_fraction="0.005",
        entry_price="200",
        stop_price="210",
        direction="short",
    )
    # risk=$250; per-share risk=$10 -> 25 shares
    assert r.qty == Decimal("25")
    assert r.binding_cap == "risk"


def test_notional_cap_binds():
    # raw qty would be 200, but notional cap of $5000 -> 50 shares max.
    r = calculate_position_size(
        equity="100000",
        risk_fraction="0.01",
        entry_price="100",
        stop_price="95",
        direction="long",
        notional_cap="5000",
    )
    assert r.qty == Decimal("50")
    assert r.binding_cap == "notional"


def test_qty_cap_binds():
    r = calculate_position_size(
        equity="100000",
        risk_fraction="0.01",
        entry_price="100",
        stop_price="95",
        direction="long",
        qty_cap="10",
    )
    assert r.qty == Decimal("10")
    assert r.binding_cap == "qty_cap"


def test_qty_step_floors_fractional():
    # risk=$1000, per-share=$3 -> raw 333.33...; step=1 -> 333
    r = calculate_position_size(
        equity="100000",
        risk_fraction="0.01",
        entry_price="100",
        stop_price="97",
        direction="long",
    )
    assert r.qty == Decimal("333")


def test_fractional_step_for_crypto():
    r = calculate_position_size(
        equity="10000",
        risk_fraction="0.01",
        entry_price="100",
        stop_price="99",
        direction="long",
        qty_step="0.01",
    )
    # risk $100; per-share $1 -> 100 units
    assert r.qty == Decimal("100.00")


def test_rejects_zero_per_share_risk():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity="100000",
            risk_fraction="0.01",
            entry_price="100",
            stop_price="100",
            direction="long",
        )
    # 'long stop must be < entry' fires first
    assert ei.value.code in ("long_stop_not_below_entry", "zero_per_share_risk")


def test_rejects_long_stop_above_entry():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity="100000",
            risk_fraction="0.01",
            entry_price="100",
            stop_price="105",
            direction="long",
        )
    assert ei.value.code == "long_stop_not_below_entry"


def test_rejects_short_stop_below_entry():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity="100000",
            risk_fraction="0.01",
            entry_price="100",
            stop_price="95",
            direction="short",
        )
    assert ei.value.code == "short_stop_not_above_entry"


def test_rejects_non_positive_equity():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity="0",
            risk_fraction="0.01",
            entry_price="100",
            stop_price="95",
            direction="long",
        )
    assert ei.value.code == "non_positive_equity"


def test_rejects_invalid_risk_fraction():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity="100000",
            risk_fraction="1.5",
            entry_price="100",
            stop_price="95",
            direction="long",
        )
    assert ei.value.code == "invalid_risk_fraction"


def test_rejects_nan():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity=float("nan"),
            risk_fraction="0.01",
            entry_price="100",
            stop_price="95",
            direction="long",
        )
    assert ei.value.code == "non_finite_input"


def test_rejects_inf():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity=float("inf"),
            risk_fraction="0.01",
            entry_price="100",
            stop_price="95",
            direction="long",
        )
    assert ei.value.code == "non_finite_input"


def test_rejects_invalid_direction():
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity="100000",
            risk_fraction="0.01",
            entry_price="100",
            stop_price="95",
            direction="sideways",  # type: ignore[arg-type]
        )
    assert ei.value.code == "invalid_direction"


def test_qty_floored_to_zero_raises():
    # Tiny equity with huge step -> raw qty < 1 -> floor to 0 -> error
    with pytest.raises(PositionSizingError) as ei:
        calculate_position_size(
            equity="100",
            risk_fraction="0.01",
            entry_price="100",
            stop_price="50",
            direction="long",
            qty_step="1",
        )
    assert ei.value.code == "qty_floored_to_zero"


def test_decimal_inputs_accepted():
    r = calculate_position_size(
        equity=Decimal("100000"),
        risk_fraction=Decimal("0.01"),
        entry_price=Decimal("100"),
        stop_price=Decimal("95"),
        direction="long",
    )
    assert r.qty == Decimal("200")


def test_notional_cap_none_uses_risk():
    r = calculate_position_size(
        equity="100000",
        risk_fraction="0.01",
        entry_price="100",
        stop_price="95",
        direction="long",
        notional_cap=None,
        qty_cap=None,
    )
    assert r.binding_cap == "risk"
    assert r.qty == Decimal("200")
