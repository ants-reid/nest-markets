"""MH-143-A — Position Sizing Service (additive only; not yet wired into worker).

This service computes a *recommended* position size from:
- account equity (USD)
- per-trade risk fraction (e.g. 0.005 = 0.5 %)
- entry price
- stop price (long: stop < entry; short: stop > entry)
- optional notional cap (USD) and quantity cap

The math is **risk-per-trade / per-share-risk**:

    risk_dollars   = equity * risk_fraction
    per_share_risk = abs(entry - stop)
    raw_qty        = risk_dollars / per_share_risk
    qty            = floor(min(raw_qty, notional_cap / entry, qty_cap))

The service rejects malformed inputs (NaN/inf/non-positive, zero distance,
risk_fraction outside (0, 1]). It returns a structured ``SizingResult`` with
the chosen qty, the binding cap, and full audit fields for downstream
recording.

DRIFT-LOCK GUARANTEE
--------------------
This module is **not yet called from any worker, route, or broker path**.
Today it only exists as a pure calculator with tests. Wiring into the
auto-paper worker is intentionally deferred to a later phase
(MH-143-B / MH-145), so worker execution behaviour is unchanged by this
phase. The function never touches the database and never calls broker
submission paths.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from typing import Literal, Optional

Direction = Literal["long", "short"]


class PositionSizingError(ValueError):
    """Raised when sizing inputs are invalid or produce a non-tradeable size."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SizingInput:
    equity: Decimal
    risk_fraction: Decimal
    entry_price: Decimal
    stop_price: Decimal
    direction: Direction
    notional_cap: Optional[Decimal] = None
    qty_cap: Optional[Decimal] = None
    # Default to whole units (stocks). Crypto/forex callers will override.
    qty_step: Decimal = Decimal("1")


@dataclass(frozen=True)
class SizingResult:
    qty: Decimal
    risk_dollars: Decimal
    per_share_risk: Decimal
    notional: Decimal
    binding_cap: str  # 'risk' | 'notional' | 'qty_cap' | 'qty_step_floor'
    inputs: SizingInput


def _to_decimal(value, name: str) -> Decimal:
    """Coerce input into Decimal, rejecting NaN/inf/None/non-numeric."""
    if value is None:
        raise PositionSizingError("missing_input", f"{name} is required")
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise PositionSizingError("non_finite_input", f"{name}={value!r}")
        try:
            d = Decimal(str(value))
        except InvalidOperation as exc:
            raise PositionSizingError(
                "invalid_input", f"{name}={value!r}"
            ) from exc
    elif isinstance(value, str):
        try:
            d = Decimal(value)
        except InvalidOperation as exc:
            raise PositionSizingError(
                "invalid_input", f"{name}={value!r}"
            ) from exc
    else:
        raise PositionSizingError(
            "invalid_input_type", f"{name} must be numeric, got {type(value).__name__}"
        )
    if d.is_nan() or d.is_infinite():
        raise PositionSizingError("non_finite_input", f"{name}={value!r}")
    return d


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise PositionSizingError("invalid_qty_step", f"qty_step must be > 0, got {step}")
    if value <= 0:
        return Decimal("0")
    n = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return n * step


def calculate_position_size(
    *,
    equity,
    risk_fraction,
    entry_price,
    stop_price,
    direction: Direction,
    notional_cap=None,
    qty_cap=None,
    qty_step="1",
) -> SizingResult:
    """Pure calculator — see module docstring for math."""
    eq = _to_decimal(equity, "equity")
    rf = _to_decimal(risk_fraction, "risk_fraction")
    ent = _to_decimal(entry_price, "entry_price")
    stp = _to_decimal(stop_price, "stop_price")
    step = _to_decimal(qty_step, "qty_step")
    n_cap = _to_decimal(notional_cap, "notional_cap") if notional_cap is not None else None
    q_cap = _to_decimal(qty_cap, "qty_cap") if qty_cap is not None else None

    if eq <= 0:
        raise PositionSizingError("non_positive_equity", f"equity must be > 0, got {eq}")
    if rf <= 0 or rf > 1:
        raise PositionSizingError(
            "invalid_risk_fraction",
            f"risk_fraction must be in (0, 1], got {rf}",
        )
    if ent <= 0:
        raise PositionSizingError(
            "non_positive_entry", f"entry_price must be > 0, got {ent}"
        )
    if stp <= 0:
        raise PositionSizingError(
            "non_positive_stop", f"stop_price must be > 0, got {stp}"
        )
    if direction not in ("long", "short"):
        raise PositionSizingError(
            "invalid_direction", f"direction must be 'long' or 'short', got {direction!r}"
        )
    if direction == "long" and stp >= ent:
        raise PositionSizingError(
            "long_stop_not_below_entry",
            f"long stop {stp} must be < entry {ent}",
        )
    if direction == "short" and stp <= ent:
        raise PositionSizingError(
            "short_stop_not_above_entry",
            f"short stop {stp} must be > entry {ent}",
        )
    if n_cap is not None and n_cap <= 0:
        raise PositionSizingError("invalid_notional_cap", f"notional_cap={n_cap}")
    if q_cap is not None and q_cap <= 0:
        raise PositionSizingError("invalid_qty_cap", f"qty_cap={q_cap}")

    per_share_risk = abs(ent - stp)
    if per_share_risk <= 0:
        raise PositionSizingError(
            "zero_per_share_risk", "entry and stop must differ"
        )

    risk_dollars = eq * rf
    raw_qty = risk_dollars / per_share_risk
    binding_cap = "risk"

    if n_cap is not None:
        qty_from_notional = n_cap / ent
        if qty_from_notional < raw_qty:
            raw_qty = qty_from_notional
            binding_cap = "notional"

    if q_cap is not None and q_cap < raw_qty:
        raw_qty = q_cap
        binding_cap = "qty_cap"

    qty = _floor_to_step(raw_qty, step)
    if qty == raw_qty:
        # No flooring happened; binding cap unchanged.
        pass
    else:
        # Flooring shaved the qty; if the result is zero, that's a hard error
        # (caller asked for a tradeable size and we cannot honour it).
        if qty == 0:
            raise PositionSizingError(
                "qty_floored_to_zero",
                f"raw_qty={raw_qty} floored to 0 by qty_step={step}",
            )
        # Otherwise still record the binding cap (it's the original cap).

    notional = qty * ent

    return SizingResult(
        qty=qty,
        risk_dollars=risk_dollars,
        per_share_risk=per_share_risk,
        notional=notional,
        binding_cap=binding_cap,
        inputs=SizingInput(
            equity=eq,
            risk_fraction=rf,
            entry_price=ent,
            stop_price=stp,
            direction=direction,
            notional_cap=n_cap,
            qty_cap=q_cap,
            qty_step=step,
        ),
    )
