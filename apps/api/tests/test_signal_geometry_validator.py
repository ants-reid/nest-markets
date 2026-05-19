"""Tests for MH-151 signal geometry validator."""

from __future__ import annotations

import math

import pytest

from app.services.signal_geometry_validator import (
    GeometryInput,
    SignalGeometryError,
    validate_geometry,
    validate_payload,
)


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_valid_long_geometry_passes():
    validate_geometry(
        GeometryInput(direction="long", entry_min=100.0, entry_max=101.0, stop_price=99.0, target_price=105.0)
    )


def test_valid_short_geometry_passes():
    validate_geometry(
        GeometryInput(direction="short", entry_min=100.0, entry_max=101.0, stop_price=102.0, target_price=95.0)
    )


def test_valid_long_with_zero_width_entry_zone_passes():
    """entry_min == entry_max is allowed (single-price entry)."""
    validate_geometry(
        GeometryInput(direction="long", entry_min=100.0, entry_max=100.0, stop_price=99.0, target_price=110.0)
    )


# ---------------------------------------------------------------------------
# Direction validation
# ---------------------------------------------------------------------------


def test_unknown_direction_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="sideways", entry_min=100, entry_max=101, stop_price=99, target_price=105)
        )
    assert exc.value.code == "invalid_direction"


def test_flat_direction_bypasses_geometry_checks():
    """'flat' = no-trade — geometry must not be enforced (entry/stop/target may be 0)."""
    validate_geometry(
        GeometryInput(direction="flat", entry_min=0.0, entry_max=0.0, stop_price=0.0, target_price=0.0)
    )


def test_empty_direction_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="", entry_min=100, entry_max=101, stop_price=99, target_price=105)
        )
    assert exc.value.code == "invalid_direction"


def test_direction_case_insensitive_and_trimmed():
    validate_geometry(
        GeometryInput(direction="  LONG  ", entry_min=100, entry_max=101, stop_price=99, target_price=105)
    )


# ---------------------------------------------------------------------------
# NaN / inf / non-positive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nan_or_inf_rejected(bad):
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=bad, entry_max=101, stop_price=99, target_price=105)
        )
    assert exc.value.code == "non_finite_value"


def test_zero_price_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=0.0, entry_max=101, stop_price=99, target_price=105)
        )
    assert exc.value.code == "non_positive_value"


def test_negative_price_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=100, entry_max=101, stop_price=-5, target_price=105)
        )
    assert exc.value.code == "non_positive_value"


# ---------------------------------------------------------------------------
# Entry zone ordering
# ---------------------------------------------------------------------------


def test_inverted_entry_zone_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=101, entry_max=100, stop_price=99, target_price=110)
        )
    assert exc.value.code == "entry_zone_inverted"


# ---------------------------------------------------------------------------
# Long-side geometry
# ---------------------------------------------------------------------------


def test_long_stop_at_entry_min_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=100, entry_max=101, stop_price=100, target_price=105)
        )
    assert exc.value.code == "long_stop_not_below_entry"


def test_long_stop_above_entry_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=100, entry_max=101, stop_price=102, target_price=105)
        )
    assert exc.value.code == "long_stop_not_below_entry"


def test_long_target_at_entry_max_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=100, entry_max=101, stop_price=99, target_price=101)
        )
    assert exc.value.code == "long_target_not_above_entry"


def test_long_target_below_entry_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="long", entry_min=100, entry_max=101, stop_price=99, target_price=98)
        )
    assert exc.value.code == "long_target_not_above_entry"


# ---------------------------------------------------------------------------
# Short-side geometry
# ---------------------------------------------------------------------------


def test_short_stop_at_entry_max_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="short", entry_min=100, entry_max=101, stop_price=101, target_price=95)
        )
    assert exc.value.code == "short_stop_not_above_entry"


def test_short_stop_below_entry_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="short", entry_min=100, entry_max=101, stop_price=99, target_price=95)
        )
    assert exc.value.code == "short_stop_not_above_entry"


def test_short_target_at_entry_min_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="short", entry_min=100, entry_max=101, stop_price=102, target_price=100)
        )
    assert exc.value.code == "short_target_not_below_entry"


def test_short_target_above_entry_rejected():
    with pytest.raises(SignalGeometryError) as exc:
        validate_geometry(
            GeometryInput(direction="short", entry_min=100, entry_max=101, stop_price=102, target_price=105)
        )
    assert exc.value.code == "short_target_not_below_entry"


# ---------------------------------------------------------------------------
# Payload-shaped validator
# ---------------------------------------------------------------------------


def test_validate_payload_happy_path():
    validate_payload(
        {
            "direction": "long",
            "entry_zone": [100.0, 101.0],
            "stop_price": 99.0,
            "target_price": 105.0,
        }
    )


def test_validate_payload_rejects_non_dict():
    with pytest.raises(SignalGeometryError) as exc:
        validate_payload("not a dict")  # type: ignore[arg-type]
    assert exc.value.code == "invalid_payload"


def test_validate_payload_rejects_bad_entry_zone_shape():
    with pytest.raises(SignalGeometryError) as exc:
        validate_payload(
            {"direction": "long", "entry_zone": [100.0], "stop_price": 99.0, "target_price": 105.0}
        )
    assert exc.value.code == "invalid_entry_zone"


def test_validate_payload_rejects_missing_field():
    with pytest.raises(SignalGeometryError) as exc:
        validate_payload({"direction": "long", "entry_zone": [100, 101], "stop_price": 99})
    assert exc.value.code == "invalid_geometry_field"


def test_validate_payload_propagates_geometry_error():
    with pytest.raises(SignalGeometryError) as exc:
        validate_payload(
            {
                "direction": "long",
                "entry_zone": [100.0, 101.0],
                "stop_price": 102.0,
                "target_price": 110.0,
            }
        )
    assert exc.value.code == "long_stop_not_below_entry"


def test_validate_payload_rejects_nan_in_entry_zone():
    with pytest.raises(SignalGeometryError):
        validate_payload(
            {
                "direction": "long",
                "entry_zone": [math.nan, 101.0],
                "stop_price": 99.0,
                "target_price": 105.0,
            }
        )
