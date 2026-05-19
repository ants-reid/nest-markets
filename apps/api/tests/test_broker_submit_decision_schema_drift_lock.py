"""Cycle 33 — Schema drift-lock for ``broker_submit_decisions`` (MH-148-A).

The MH-148-A table shipped with a deliberate column shape designed to
let the deferred MH-148-C writer evolve without schema coupling. Until
MH-148-C lands, the column set / nullability / type-family must remain
exactly as shipped. Any divergence is a silent schema drift that must
be reviewed under a named matrix phase.

Uses pure SQLAlchemy ``__table__.columns`` introspection — no DB.

Drift-lock notes:
    * Pure additive test; no production code change.
    * No imports of ``trading_control_service`` or ``BrokerService``.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.broker_submit_decision import BrokerSubmitDecision


# Cycle-23 ship state — column name → (nullable, expected SQLAlchemy type
# class). ``id`` and ``created_at`` come from mixins; we assert their
# presence + key invariants without binding to a specific type class so
# the mixin contract can evolve under its own phase.
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type]] = {
    "signal_id": (True, UUID),
    "intent": (False, String),
    "would_block": (False, Boolean),
    "blocked_reason_code": (True, String),
    "blocked_reason_text": (True, String),
    "preflight_json": (True, type(None)),  # JSONBType — checked separately
}


def test_table_name_unchanged():
    assert BrokerSubmitDecision.__tablename__ == "broker_submit_decisions"


def test_business_column_set_unchanged():
    """The business-column set (excluding mixin-supplied ``id`` /
    ``created_at``) must match the cycle-23 ship state exactly."""
    table_cols = set(BrokerSubmitDecision.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"BrokerSubmitDecision is missing column(s): {sorted(missing)}. "
        "If you intend to drop columns, ship a matrix phase + migration "
        "+ ledger entry."
    )
    assert not extra, (
        f"BrokerSubmitDecision has unexpected new column(s): "
        f"{sorted(extra)}. If you intend to add columns, ship a matrix "
        "phase + migration + ledger entry and update this test."
    )


def test_business_column_nullability_unchanged():
    """``intent`` and ``would_block`` must remain NOT NULL; everything
    else nullable. Flipping any nullability is a behaviour change."""
    for col_name, (expected_nullable, _expected_type) in EXPECTED_BUSINESS_COLUMNS.items():
        col = BrokerSubmitDecision.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"BrokerSubmitDecision.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}. Schema "
            "drift — ship a matrix phase + migration + ledger entry."
        )


def test_business_column_type_families_unchanged():
    """Type-family check (not exact type-class identity) for the
    NULL-nullable text/uuid/bool columns; ``preflight_json`` is a
    JSONBType and is checked by name."""
    cols = BrokerSubmitDecision.__table__.columns
    assert isinstance(cols["signal_id"].type, UUID), "signal_id type drifted"
    assert isinstance(cols["intent"].type, String), "intent type drifted"
    assert isinstance(cols["would_block"].type, Boolean), "would_block type drifted"
    assert isinstance(cols["blocked_reason_code"].type, String), "blocked_reason_code type drifted"
    assert isinstance(cols["blocked_reason_text"].type, String), "blocked_reason_text type drifted"
    # preflight_json — JSONBType is the project's portable JSONB shim
    # which resolves to PG ``JSONB`` (or a SQLite JSON shim under tests).
    # Match by class name to avoid binding to its import path.
    json_type_name = type(cols["preflight_json"].type).__name__
    assert json_type_name in {"JSONBType", "JSONB", "JSON"}, (
        f"preflight_json must remain JSONB-family typed (got {json_type_name})."
    )


def test_string_lengths_unchanged():
    """``intent`` was sized 32 and the two reason fields 64/500 to match
    the writer contract documented in MH-148-A. Length drift is a
    schema-level behaviour change."""
    cols = BrokerSubmitDecision.__table__.columns
    assert cols["intent"].type.length == 32, "intent length drifted"
    assert cols["blocked_reason_code"].type.length == 64, "blocked_reason_code length drifted"
    assert cols["blocked_reason_text"].type.length == 500, "blocked_reason_text length drifted"


def test_id_and_created_at_still_supplied_by_mixins():
    """Sanity: the mixin-supplied bookkeeping columns must still be
    present. (Their internal types are owned by the mixin contract.)"""
    cols = BrokerSubmitDecision.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in BrokerSubmitDecision.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"
