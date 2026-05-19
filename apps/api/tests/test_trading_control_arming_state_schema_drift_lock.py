"""Cycle 39 — Schema drift-lock for ``trading_control_arming_states``.

The durable state row for trading-control arming posture. This is the
single most safety-critical config table in the system — the row that
controls whether enforcement is "armed" or "disarmed" for a given
(scope, trading_mode) pair.

Locks down:
  * 15 business columns + nullability + String lengths
  * Default ``state = 'disarmed'`` (anti-escalation: a freshly-seeded
    arming row must be DISARMED, never armed)
  * Unique constraint on ``(scope, trading_mode)`` so a (scope, mode)
    pair has exactly one arming state row
  * Two composite indexes
  * Four CHECK constraints verified via ``pg_get_constraintdef``:
      - ``ck_..._state``: state ∈ {armed, disarmed}
      - ``ck_..._enablement_status``: status ∈ {ready, blocked, warning}
        or NULL
      - ``ck_..._armed_fields``: state='armed' implies armed_at,
        armed_by, expires_at all NOT NULL
      - ``ck_..._disarmed_expiry``: state='disarmed' implies
        expires_at IS NULL

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection + ``pg_*`` catalog reads.
"""

from __future__ import annotations

from sqlalchemy import DateTime, String, Text, UniqueConstraint, text

from app.db.models.trading_control_arming_state import TradingControlArmingState
from app.db.session import SessionLocal


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "scope": (False, String, 50),
    "trading_mode": (False, String, 20),
    "state": (False, String, 20),
    "armed_at": (True, DateTime, None),
    "armed_by": (True, String, 100),
    "arm_reason": (True, Text, None),
    "expires_at": (True, DateTime, None),
    "last_enablement_checked_at": (True, DateTime, None),
    "last_enablement_status": (True, String, 20),
    "last_enablement_blockers": (True, type(None), None),  # JSON
    "last_enablement_warnings": (True, type(None), None),  # JSON
    "client_request_id": (True, String, 100),
    "disarmed_at": (True, DateTime, None),
    "disarmed_by": (True, String, 100),
    "disarm_reason": (True, Text, None),
    "metadata_json": (True, type(None), None),  # JSON
}


# CHECK constraint name → required substring(s) in pg_get_constraintdef.
EXPECTED_CHECK_CONSTRAINTS: dict[str, list[str]] = {
    "ck_trading_control_arming_states_state": ["armed", "disarmed"],
    "ck_trading_control_arming_states_enablement_status": [
        "ready",
        "blocked",
        "warning",
    ],
    "ck_trading_control_arming_states_armed_fields": [
        "armed_at",
        "armed_by",
        "expires_at",
    ],
    "ck_trading_control_arming_states_disarmed_expiry": [
        "disarmed",
        "expires_at",
    ],
}


EXPECTED_INDEXES: dict[str, list[str]] = {
    "ix_trading_control_arming_states_state_expires_at": ["state", "expires_at"],
    "ix_trading_control_arming_states_updated_at": ["updated_at"],
}


# --------------------------------------------------------------------------- #
# Table-level invariants                                                      #
# --------------------------------------------------------------------------- #


def test_table_name_unchanged():
    assert TradingControlArmingState.__tablename__ == "trading_control_arming_states"


def test_business_column_set_unchanged():
    table_cols = set(TradingControlArmingState.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"TradingControlArmingState is missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"TradingControlArmingState has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = TradingControlArmingState.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"TradingControlArmingState.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = TradingControlArmingState.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"TradingControlArmingState.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


# --------------------------------------------------------------------------- #
# Anti-escalation: state defaults to 'disarmed'                               #
# --------------------------------------------------------------------------- #


def test_state_default_is_disarmed():
    """A freshly-seeded arming row must be DISARMED, never armed.
    ANTI-ESCALATION GUARANTEE."""
    col = TradingControlArmingState.__table__.columns["state"]
    assert col.default is not None, (
        "TradingControlArmingState.state must keep its Python default of "
        "'disarmed' — ANTI-ESCALATION GUARANTEE."
    )
    assert col.default.arg == "disarmed", (
        f"TradingControlArmingState.state Python default drifted: "
        f"expected 'disarmed', got {col.default.arg!r}. "
        "ANTI-ESCALATION DRIFT."
    )
    assert col.server_default is not None
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "disarmed" in str(server_default_value), (
        f"TradingControlArmingState.state server_default drifted: "
        f"expected 'disarmed', got {server_default_value!r}. "
        "ANTI-ESCALATION DRIFT."
    )


# --------------------------------------------------------------------------- #
# Unique constraint                                                           #
# --------------------------------------------------------------------------- #


def test_unique_constraint_scope_mode_present():
    uniques = [
        c
        for c in TradingControlArmingState.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    by_name = {u.name: u for u in uniques}
    name = "uq_trading_control_arming_states_scope_mode"
    assert name in by_name, (
        f"TradingControlArmingState is missing UniqueConstraint {name!r}. "
        "Without it, a (scope, trading_mode) pair could have multiple "
        "arming rows simultaneously."
    )
    cols = [c.name for c in by_name[name].columns]
    assert cols == ["scope", "trading_mode"], (
        f"UniqueConstraint columns drifted: expected "
        f"['scope', 'trading_mode'], got {cols}."
    )


# --------------------------------------------------------------------------- #
# CHECK constraints — pinned via pg_get_constraintdef                         #
# --------------------------------------------------------------------------- #


def test_expected_check_constraints_present_in_db():
    """All four CHECK constraints must remain in the live DB and
    reference their required values/columns.

    Most critically, ``ck_..._armed_fields`` enforces at the DB layer
    that no row can be ``state = 'armed'`` without armed_at, armed_by,
    AND expires_at all populated. If that constraint silently
    disappears, an arming row could be marked armed without a
    countdown to disarm.
    """
    with SessionLocal() as session:
        rows = session.execute(
            text(
                """
                SELECT conname, pg_get_constraintdef(oid) AS def
                FROM pg_constraint
                WHERE conrelid = 'trading_control_arming_states'::regclass
                  AND contype = 'c'
                """
            )
        ).all()
    by_name = {row.conname: (row.def_ if hasattr(row, "def_") else row[1]) for row in rows}
    for expected_name, required_substrings in EXPECTED_CHECK_CONSTRAINTS.items():
        assert expected_name in by_name, (
            f"CHECK constraint {expected_name!r} is missing from the "
            "live DB. Run ``alembic upgrade head`` and verify the "
            "trading_control_arming_states migration is applied. "
            "DO NOT drop these constraints without an explicit unlock "
            "phase — they are the core safety guards."
        )
        constraint_def = by_name[expected_name]
        for substr in required_substrings:
            assert substr in constraint_def, (
                f"CHECK constraint {expected_name} drifted; expected "
                f"to reference {substr!r}. Got: {constraint_def!r}."
            )


# --------------------------------------------------------------------------- #
# Indexes                                                                     #
# --------------------------------------------------------------------------- #


def test_expected_indexes_present_orm():
    indexes_by_name = {
        idx.name: idx for idx in TradingControlArmingState.__table__.indexes
    }
    for expected_name, expected_cols in EXPECTED_INDEXES.items():
        assert expected_name in indexes_by_name, (
            f"ORM-declared index {expected_name!r} is missing."
        )
        actual_cols = [c.name for c in indexes_by_name[expected_name].columns]
        assert actual_cols == expected_cols, (
            f"Index {expected_name} columns drifted: expected "
            f"{expected_cols}, got {actual_cols}."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = TradingControlArmingState.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in TradingControlArmingState.__table__.primary_key.columns]
    assert pk_cols == ["id"]
