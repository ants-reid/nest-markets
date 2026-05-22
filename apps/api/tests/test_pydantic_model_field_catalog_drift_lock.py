"""Drift-lock pin: field name + type catalog of safety-critical Pydantic
schemas.

Cycle 61 — MH-DRIFTLOCK-PYDANTIC-MODEL-FIELD-CATALOG.

Why this pin exists
-------------------
``OrderRequestSchema``, ``OrderResultSchema``, ``BrokerModeSchema``, and
``TradingControlSchema`` are the API boundary schemas for everything
adjacent to broker submission and trading-control reporting.  A silent
field rename (e.g. ``side`` → ``direction``), retype
(``quantity: float`` → ``quantity: int``), or required-flag flip
(``ticker: required`` → optional) would change the request/response
contract that downstream consumers — including the cockpit UI and audit
log writers — rely on.

This pin freezes the field name set, annotation string, and required-flag
on each of those schemas.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

from app.schemas import broker_schemas as bs

# (schema_name) -> {field_name: (annotation_str, required_bool)}
# annotation_str is the str() of the field annotation (with ``typing.``
# stripped for portability).  This is intentionally byte-equal so a silent
# retype is caught.
EXPECTED_SCHEMA_FIELDS: dict[str, dict[str, tuple[str, bool]]] = {
    "OrderRequestSchema": {
        "ticker": ("<class 'str'>", True),
        "side": ("<class 'str'>", True),
        "quantity": ("<class 'float'>", True),
        "order_type": ("<class 'str'>", True),
        "limit_price": ("float | None", False),
        "stop_price": ("float | None", False),
        "tif": ("<class 'str'>", False),
        "outside_rth": ("<class 'bool'>", False),
        "client_order_id": ("str | None", False),
    },
    "OrderResultSchema": {
        "broker_order_id": ("<class 'str'>", True),
        "status": ("<class 'str'>", True),
        "filled_price": ("float | None", False),
        "filled_quantity": ("float | None", False),
        "error_message": ("str | None", False),
        "broker_mode": (
            "app.schemas.broker_schemas.BrokerModeSchema | None",
            False,
        ),
        "execution_source": ("<class 'str'>", False),
        "balance_source": ("<class 'str'>", False),
        "fees_source": ("<class 'str'>", False),
        "fills_source": ("<class 'str'>", False),
    },
    "BrokerModeSchema": {
        "broker": ("<class 'str'>", True),
        "mode": ("<class 'str'>", True),
        "live_execution_enabled": ("<class 'bool'>", True),
        "paper_trading_enabled": ("<class 'bool'>", True),
    },
    "TradingControlSchema": {
        "trading_mode": ("<class 'str'>", True),
        "execution_control": ("<class 'str'>", True),
        "arming_state": ("<class 'str'>", True),
        "live_order_submission_allowed": ("<class 'bool'>", True),
        "paper_order_submission_allowed": ("<class 'bool'>", True),
        "auto_trading_allowed": ("<class 'bool'>", True),
        "emergency_stop_active": ("<class 'bool'>", True),
        "reasons": ("list[str]", False),
    },
}

# Subset of (schema, field) pairs whose presence + required-flag is part of
# the safety contract.  These are the fields the cockpit + audit logger
# index by; renaming or making optional any of them silently breaks
# attribution.
SAFETY_REQUIRED_FIELDS: set[tuple[str, str]] = {
    ("OrderRequestSchema", "ticker"),
    ("OrderRequestSchema", "side"),
    ("OrderRequestSchema", "quantity"),
    ("OrderRequestSchema", "order_type"),
    ("OrderResultSchema", "broker_order_id"),
    ("OrderResultSchema", "status"),
    ("BrokerModeSchema", "broker"),
    ("BrokerModeSchema", "mode"),
    ("BrokerModeSchema", "live_execution_enabled"),
    ("BrokerModeSchema", "paper_trading_enabled"),
    ("TradingControlSchema", "auto_trading_allowed"),
    ("TradingControlSchema", "live_order_submission_allowed"),
    ("TradingControlSchema", "emergency_stop_active"),
    ("TradingControlSchema", "arming_state"),
}


def _annotation_repr(annotation: object) -> str:
    return str(annotation).replace("typing.", "")


def _collect_actual_fields(name: str) -> dict[str, tuple[str, bool]]:
    cls = getattr(bs, name)
    return {
        n: (_annotation_repr(f.annotation), bool(f.is_required()))
        for n, f in cls.model_fields.items()
    }


def test_safety_schema_field_catalog_exact_match() -> None:
    failures: list[str] = []
    for schema_name, expected in EXPECTED_SCHEMA_FIELDS.items():
        actual = _collect_actual_fields(schema_name)
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)
        if missing or extra:
            failures.append(
                f"  {schema_name}: missing={sorted(missing)} extra={sorted(extra)}"
            )
            continue
        for fname, exp in expected.items():
            got = actual[fname]
            if got != exp:
                failures.append(
                    f"  {schema_name}.{fname}: expected={exp!r} got={got!r}"
                )
    assert not failures, (
        "Safety-critical Pydantic schema field-catalog drift detected. "
        "These schemas are the API boundary that the cockpit + audit log "
        "depend on.\n" + "\n".join(failures)
    )


def test_safety_required_fields_remain_required() -> None:
    """The hard-safety subset of fields must remain present AND required.

    A silent rename or required→optional flip on any of these breaks
    audit/attribution downstream.
    """
    failures: list[str] = []
    for schema_name, fname in SAFETY_REQUIRED_FIELDS:
        actual = _collect_actual_fields(schema_name)
        if fname not in actual:
            failures.append(f"  {schema_name}.{fname} MISSING")
            continue
        _, required = actual[fname]
        if not required:
            failures.append(
                f"  {schema_name}.{fname} is no longer required"
            )
    assert not failures, (
        "SAFETY_REQUIRED Pydantic fields drift detected:\n"
        + "\n".join(failures)
    )


def test_safety_required_subset_is_subset_of_full_catalog() -> None:
    """Sanity guard: every (schema, field) in the safety subset must
    appear in the full EXPECTED_SCHEMA_FIELDS catalog."""
    full = {
        (s, f) for s, fields in EXPECTED_SCHEMA_FIELDS.items() for f in fields
    }
    missing = SAFETY_REQUIRED_FIELDS - full
    assert not missing, (
        f"SAFETY_REQUIRED_FIELDS contains pairs not present in "
        f"EXPECTED_SCHEMA_FIELDS: {sorted(missing)}"
    )
