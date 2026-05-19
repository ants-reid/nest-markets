"""MH-151 — Signal geometry validation.

Rejects malformed signals before they can flow downstream. Validates:
- ``entry_zone`` finite, ordered (min ≤ max), positive
- ``stop_price`` and ``target_price`` finite and positive
- For ``long`` direction: ``stop < entry_min`` and ``target > entry_max``
- For ``short`` direction: ``stop > entry_max`` and ``target < entry_min``
- ``stop`` must not equal entry zone bounds (zero-distance stop is rejected)
- ``target`` must not equal entry zone bounds (zero-distance target is rejected)

This is a *validator*, not an enforcer — it raises an exception when geometry
is unsafe so the caller can surface a structured error. It does not silently
mutate the signal, and it does not enable, allow, or block any trading
action by itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

VALID_DIRECTIONS = ("long", "short")
# 'flat' is a valid LLM output meaning "no trade" — geometry checks do not apply.
NO_TRADE_DIRECTIONS = ("flat",)


class SignalGeometryError(ValueError):
    """Raised when a signal's price geometry is unsafe or malformed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class GeometryInput:
    """Minimal geometric fields needed to validate a signal."""

    direction: str
    entry_min: float
    entry_max: float
    stop_price: float
    target_price: float


def _is_finite_positive(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def _check_all_finite(values: Iterable[tuple[str, float]]) -> None:
    for name, val in values:
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            raise SignalGeometryError(
                "non_finite_value",
                f"{name} must be a finite number, got {val!r}",
            )
        if val <= 0:
            raise SignalGeometryError(
                "non_positive_value",
                f"{name} must be > 0, got {val!r}",
            )


def validate_geometry(geom: GeometryInput) -> None:
    """Raise ``SignalGeometryError`` if the geometry is unsafe.

    No-trade directions (``flat``) bypass geometry checks because there is no
    real entry/stop/target to validate.
    """
    direction = (geom.direction or "").strip().lower()
    if direction in NO_TRADE_DIRECTIONS:
        return
    if direction not in VALID_DIRECTIONS:
        raise SignalGeometryError(
            "invalid_direction",
            f"direction must be one of {VALID_DIRECTIONS + NO_TRADE_DIRECTIONS}, got {geom.direction!r}",
        )

    _check_all_finite(
        [
            ("entry_min", geom.entry_min),
            ("entry_max", geom.entry_max),
            ("stop_price", geom.stop_price),
            ("target_price", geom.target_price),
        ]
    )

    if geom.entry_min > geom.entry_max:
        raise SignalGeometryError(
            "entry_zone_inverted",
            f"entry_min ({geom.entry_min}) must be ≤ entry_max ({geom.entry_max})",
        )

    if direction == "long":
        if geom.stop_price >= geom.entry_min:
            raise SignalGeometryError(
                "long_stop_not_below_entry",
                f"long stop ({geom.stop_price}) must be < entry_min ({geom.entry_min})",
            )
        if geom.target_price <= geom.entry_max:
            raise SignalGeometryError(
                "long_target_not_above_entry",
                f"long target ({geom.target_price}) must be > entry_max ({geom.entry_max})",
            )
    else:  # short
        if geom.stop_price <= geom.entry_max:
            raise SignalGeometryError(
                "short_stop_not_above_entry",
                f"short stop ({geom.stop_price}) must be > entry_max ({geom.entry_max})",
            )
        if geom.target_price >= geom.entry_min:
            raise SignalGeometryError(
                "short_target_not_below_entry",
                f"short target ({geom.target_price}) must be < entry_min ({geom.entry_min})",
            )


def validate_payload(payload: dict) -> None:
    """Validate a raw LLM signal payload (dict) before downstream conversion.

    Expects ``direction``, ``entry_zone`` (2-tuple/list), ``stop_price``,
    ``target_price`` keys. Raises ``SignalGeometryError`` on any failure.
    """
    if not isinstance(payload, dict):
        raise SignalGeometryError("invalid_payload", "payload must be a dict")

    entry_zone = payload.get("entry_zone")
    if not isinstance(entry_zone, (list, tuple)) or len(entry_zone) != 2:
        raise SignalGeometryError(
            "invalid_entry_zone",
            f"entry_zone must be a 2-element list/tuple, got {entry_zone!r}",
        )

    try:
        entry_min = float(entry_zone[0])
        entry_max = float(entry_zone[1])
        stop_price = float(payload["stop_price"])
        target_price = float(payload["target_price"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SignalGeometryError(
            "invalid_geometry_field",
            f"could not coerce geometry fields to float: {exc}",
        ) from exc

    validate_geometry(
        GeometryInput(
            direction=str(payload.get("direction", "")),
            entry_min=entry_min,
            entry_max=entry_max,
            stop_price=stop_price,
            target_price=target_price,
        )
    )
