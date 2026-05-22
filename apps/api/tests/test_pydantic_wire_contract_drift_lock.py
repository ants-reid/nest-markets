"""Cycle 55 — Pydantic wire-contract pin.

Pins the **field names, types, defaults, and required-vs-optional**
status of the Pydantic schemas that form the wire contract between
the API and external consumers (frontend, IBKR gateway adapters,
external monitoring).

Why this matters:
  * Renaming a field silently breaks the frontend (which still sends
    the old name; FastAPI returns 422 the user never sees clearly).
  * Changing a field from required to optional silently allows
    malformed orders through validation that previously blocked them.
  * Changing a default value silently changes what gets persisted
    when the caller omits the field — e.g. ``tif`` flipping from
    "DAY" to "GTC" would silently leave orders alive overnight.
  * Adding a new required field silently breaks every existing caller.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Auto-trading gate ``assert_auto_trading_allowed()`` unchanged.
    * Schemas pinned here are for ORDER SUBMISSION (the very surface
      that ``submit_auto_order`` consumes), so this lock is part of
      the safety perimeter.

How to update this pin:
  When intentionally adding/renaming/retyping a field, update the
  pinned spec in this file in the SAME PR. The deliberate update IS
  the review signal that the wire contract is changing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.broker_schemas import (
    BrokerModeSchema,
    OrderRequestSchema,
    OrderResultSchema,
)
from app.schemas.signal import SignalResponse


# ── helpers ─────────────────────────────────────────────────────────────


def _field_spec(model_cls: type[BaseModel]) -> dict[str, dict[str, Any]]:
    """Return a stable, comparable spec for every field on a Pydantic v2 model.

    Keys: field name. Values: dict with ``required`` (bool), ``default``
    (the default value, or the sentinel string ``"<no-default>"``), and
    ``annotation`` (str repr of the type, normalized).
    """
    out: dict[str, dict[str, Any]] = {}
    for name, field in model_cls.model_fields.items():
        default: Any
        if field.is_required():
            default = "<no-default>"
        else:
            df = field.default
            # Pydantic v2 uses PydanticUndefined for "no default" alongside
            # is_required(); guard it explicitly.
            try:
                from pydantic_core import PydanticUndefined  # type: ignore[import-not-found]
                if df is PydanticUndefined:
                    default = "<no-default>"
                else:
                    default = df
            except Exception:  # pragma: no cover - import shape varies
                default = df
        out[name] = {
            "required": field.is_required(),
            "default": default,
            "annotation": str(field.annotation),
        }
    return out


def _check(model_cls: type[BaseModel], expected: dict[str, dict[str, Any]]) -> None:
    actual = _field_spec(model_cls)
    missing = set(expected) - set(actual)
    extra = set(actual) - set(expected)
    assert not missing, (
        f"{model_cls.__name__} is missing pinned field(s): {sorted(missing)}. "
        "Removing/renaming a wire field is a breaking change — every "
        "existing caller silently fails validation."
    )
    assert not extra, (
        f"{model_cls.__name__} has unexpected new field(s): {sorted(extra)}. "
        "Adding a field to the wire contract is a deliberate change "
        "that requires updating this pin in the same PR."
    )
    for name, spec in expected.items():
        a = actual[name]
        assert a["required"] == spec["required"], (
            f"{model_cls.__name__}.{name} required-flag drifted: "
            f"expected required={spec['required']}, got required={a['required']}. "
            "Required→optional silently allows malformed payloads through; "
            "optional→required silently breaks every existing caller."
        )
        assert a["default"] == spec["default"], (
            f"{model_cls.__name__}.{name} default drifted: "
            f"expected {spec['default']!r}, got {a['default']!r}. "
            "Defaults are part of the wire contract — drift here silently "
            "changes what gets persisted when the caller omits the field."
        )
        # Annotation comparison is string-based; normalize whitespace.
        actual_ann = " ".join(a["annotation"].split())
        expected_ann = " ".join(spec["annotation"].split())
        assert actual_ann == expected_ann, (
            f"{model_cls.__name__}.{name} type drifted: "
            f"expected {expected_ann!r}, got {actual_ann!r}."
        )


# ── BrokerModeSchema ────────────────────────────────────────────────────
# Surfaces paper/live isolation state. Drift here would silently break
# the safety-mode read path on every UI surface.
EXPECTED_BROKER_MODE: dict[str, dict[str, Any]] = {
    "broker": {"required": True, "default": "<no-default>", "annotation": "<class 'str'>"},
    "mode": {"required": True, "default": "<no-default>", "annotation": "<class 'str'>"},
    "live_execution_enabled": {"required": True, "default": "<no-default>", "annotation": "<class 'bool'>"},
    "paper_trading_enabled": {"required": True, "default": "<no-default>", "annotation": "<class 'bool'>"},
}


# ── OrderRequestSchema ──────────────────────────────────────────────────
# Critical: this is the request body that ``submit_order`` consumes.
# Any rename/retype here silently breaks the frontend submit flow.
# ``tif`` defaulting to "DAY" is a SAFETY DEFAULT — drift to "GTC"
# would silently leave orders alive overnight.
# ``outside_rth`` defaulting to False is a SAFETY DEFAULT — drift to
# True would silently allow off-hours fills with no liquidity.
EXPECTED_ORDER_REQUEST: dict[str, dict[str, Any]] = {
    "ticker": {"required": True, "default": "<no-default>", "annotation": "<class 'str'>"},
    "side": {"required": True, "default": "<no-default>", "annotation": "<class 'str'>"},
    "quantity": {"required": True, "default": "<no-default>", "annotation": "<class 'float'>"},
    "order_type": {"required": True, "default": "<no-default>", "annotation": "<class 'str'>"},
    "limit_price": {"required": False, "default": None, "annotation": "float | None"},
    "stop_price": {"required": False, "default": None, "annotation": "float | None"},
    "tif": {"required": False, "default": "DAY", "annotation": "<class 'str'>"},
    "outside_rth": {"required": False, "default": False, "annotation": "<class 'bool'>"},
    "client_order_id": {"required": False, "default": None, "annotation": "str | None"},
}


# ── OrderResultSchema ───────────────────────────────────────────────────
# Returned to the caller after submission. Drift here silently breaks
# every audit-trail consumer.
EXPECTED_ORDER_RESULT: dict[str, dict[str, Any]] = {
    "broker_order_id": {"required": True, "default": "<no-default>", "annotation": "<class 'str'>"},
    "status": {"required": True, "default": "<no-default>", "annotation": "<class 'str'>"},
    "filled_price": {"required": False, "default": None, "annotation": "float | None"},
    "filled_quantity": {"required": False, "default": None, "annotation": "float | None"},
    "error_message": {"required": False, "default": None, "annotation": "str | None"},
    "broker_mode": {
        "required": False,
        "default": None,
        "annotation": "app.schemas.broker_schemas.BrokerModeSchema | None",
    },
    "execution_source": {"required": False, "default": "ibkr_paper", "annotation": "<class 'str'>"},
    "balance_source": {"required": False, "default": "ibkr_paper", "annotation": "<class 'str'>"},
    "fees_source": {"required": False, "default": "ibkr_reported", "annotation": "<class 'str'>"},
    "fills_source": {"required": False, "default": "ibkr_paper", "annotation": "<class 'str'>"},
    "positions_source": {"required": False, "default": "ibkr_paper", "annotation": "<class 'str'>"},
    "serious_paper_source": {"required": False, "default": "ibkr_paper", "annotation": "<class 'str'>"},
    "is_canonical_paper": {"required": False, "default": True, "annotation": "<class 'bool'>"},
    "paper_path_note": {
        "required": False,
        "default": "IBKR paper is the canonical serious paper trading path.",
        "annotation": "<class 'str'>",
    },
}


# ── tests ───────────────────────────────────────────────────────────────


def test_broker_mode_schema_wire_contract_unchanged():
    _check(BrokerModeSchema, EXPECTED_BROKER_MODE)


def test_order_request_schema_wire_contract_unchanged():
    _check(OrderRequestSchema, EXPECTED_ORDER_REQUEST)


def test_order_request_safety_defaults_pinned():
    """Defensive double-check on the two SAFETY-RELEVANT defaults:
       * ``tif`` must default to "DAY" (NOT "GTC") so unattended
         orders die at end of day.
       * ``outside_rth`` must default to False so off-hours fills
         require deliberate opt-in by the caller."""
    fields = OrderRequestSchema.model_fields
    assert fields["tif"].default == "DAY", (
        "OrderRequestSchema.tif default drifted away from 'DAY'. "
        "Drift to 'GTC' or 'GTD' silently leaves orders alive past "
        "the trading session."
    )
    assert fields["outside_rth"].default is False, (
        "OrderRequestSchema.outside_rth default drifted to True. "
        "Off-hours fills require deliberate caller opt-in — never "
        "as a default."
    )


def test_order_result_schema_wire_contract_unchanged():
    _check(OrderResultSchema, EXPECTED_ORDER_RESULT)


def test_signal_response_required_safety_fields_present():
    """SignalResponse has many fields with complex Literal types that
    are too noisy to pin verbatim, but the SAFETY-CRITICAL fields
    must always be required and float-typed:
      * ``signal_score`` (used by risk gate threshold)
      * ``confidence`` (used by risk gate threshold)
      * ``should_trade`` (used as a hard gate)
      * ``direction`` (drives long/short/flat routing)
      * ``stop_price`` (mandatory for risk sizing)
    """
    spec = _field_spec(SignalResponse)

    for name in ("signal_score", "confidence", "should_trade", "direction", "stop_price"):
        assert name in spec, (
            f"SignalResponse.{name} is missing — this is a SAFETY-CRITICAL "
            "field consumed by the risk gate. Removing it silently bypasses "
            "the gate."
        )
        assert spec[name]["required"], (
            f"SignalResponse.{name} is no longer required. The risk gate "
            "assumes this field is always present; making it optional "
            "silently allows None to bypass the threshold check."
        )

    # Pin the numeric types of the gate-input fields (cannot drift to str
    # without breaking the comparison).
    assert "float" in spec["signal_score"]["annotation"], (
        "SignalResponse.signal_score is no longer float-typed."
    )
    assert "float" in spec["confidence"]["annotation"], (
        "SignalResponse.confidence is no longer float-typed."
    )
    assert "float" in spec["stop_price"]["annotation"], (
        "SignalResponse.stop_price is no longer float-typed."
    )
    assert "bool" in spec["should_trade"]["annotation"], (
        "SignalResponse.should_trade is no longer bool-typed."
    )


def test_signal_response_extra_forbid():
    """``model_config = ConfigDict(extra='forbid')`` is a SAFETY contract:
    drift to ``allow`` or ``ignore`` would silently accept unknown
    payload fields, which could mask typos in safety-relevant
    fields (e.g. caller sends ``shoud_trade=True`` and the gate
    silently treats ``should_trade`` as missing/falsy)."""
    cfg = SignalResponse.model_config
    extra = cfg.get("extra") if isinstance(cfg, dict) else getattr(cfg, "extra", None)
    assert extra == "forbid", (
        f"SignalResponse model_config['extra'] drifted to {extra!r}. "
        "Must remain 'forbid' so that typos in safety-critical field "
        "names cause a loud 422 instead of silent gate bypass."
    )
