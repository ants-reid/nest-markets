"""Cycle 34 — Schema drift-lock for ``risk_decisions`` (mirror of cycle 33).

The ``risk_decisions`` table accreted MH-153-A (``risk_profile_id``)
and MH-154-A (``block_reason_code``) columns under deferred-writer
matrix entries. Until the writers (MH-153-B / MH-154-B) ship, the
table's full column set / nullability / type families must remain
exactly as currently shipped.

Uses pure SQLAlchemy ``__table__.columns`` introspection — no DB.

Drift-lock notes:
    * Pure additive test; no production code change.
    * No imports of ``trading_control_service`` or ``BrokerService``.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.risk_decision import RiskDecision


# Ship state — column name → (nullable, expected SQLAlchemy type class).
# ``id`` and ``created_at`` come from mixins; their presence is asserted
# separately, their internals are owned by the mixin contract.
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type]] = {
    "signal_id": (True, UUID),
    "approved": (False, String),
    "timestamp": (True, DateTime),
    "blocking_rule": (True, String),
    "blocked_reasons_json": (True, type(None)),  # JSONB-family
    "position_risk_pct": (True, Numeric),
    "notional_allowed": (True, Numeric),
    "correlation_bucket": (True, String),
    "spread_ok": (True, Boolean),
    "session_ok": (True, Boolean),
    "drawdown_ok": (True, Boolean),
    "cooldown_ok": (True, Boolean),
    "kill_switch_active": (True, Boolean),
    "decision_json": (True, type(None)),  # JSONB-family
    "risk_profile_id": (True, UUID),  # MH-153-A
    "block_reason_code": (True, String),  # MH-154-A
}

EXPECTED_STRING_LENGTHS: dict[str, int] = {
    "approved": 20,
    "blocking_rule": 100,
    "correlation_bucket": 100,
    "block_reason_code": 64,
}


def test_table_name_unchanged():
    assert RiskDecision.__tablename__ == "risk_decisions"


def test_business_column_set_unchanged():
    """The business-column set (excluding mixin-supplied ``id`` /
    ``created_at``) must match the current ship state exactly."""
    table_cols = set(RiskDecision.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"RiskDecision is missing column(s): {sorted(missing)}. If you "
        "intend to drop columns, ship a matrix phase + migration + "
        "ledger entry."
    )
    assert not extra, (
        f"RiskDecision has unexpected new column(s): {sorted(extra)}. "
        "If you intend to add columns, ship a matrix phase + migration "
        "+ ledger entry and update this test."
    )


def test_business_column_nullability_unchanged():
    """``approved`` is the only NOT NULL business column (it has a
    server-side default of ``'pending'``); everything else nullable.
    Flipping any nullability is a behaviour change that affects writer
    contracts."""
    for col_name, (expected_nullable, _expected_type) in EXPECTED_BUSINESS_COLUMNS.items():
        col = RiskDecision.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"RiskDecision.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}. Schema drift — "
            "ship a matrix phase + migration + ledger entry."
        )


def test_business_column_type_families_unchanged():
    """Type-family check (not exact type-class identity)."""
    cols = RiskDecision.__table__.columns
    assert isinstance(cols["signal_id"].type, UUID)
    assert isinstance(cols["approved"].type, String)
    assert isinstance(cols["timestamp"].type, DateTime)
    assert isinstance(cols["blocking_rule"].type, String)
    assert isinstance(cols["position_risk_pct"].type, Numeric)
    assert isinstance(cols["notional_allowed"].type, Numeric)
    assert isinstance(cols["correlation_bucket"].type, String)
    assert isinstance(cols["spread_ok"].type, Boolean)
    assert isinstance(cols["session_ok"].type, Boolean)
    assert isinstance(cols["drawdown_ok"].type, Boolean)
    assert isinstance(cols["cooldown_ok"].type, Boolean)
    assert isinstance(cols["kill_switch_active"].type, Boolean)
    assert isinstance(cols["risk_profile_id"].type, UUID)
    assert isinstance(cols["block_reason_code"].type, String)
    # JSONB-family columns
    for json_col in ("blocked_reasons_json", "decision_json"):
        json_type_name = type(cols[json_col].type).__name__
        assert json_type_name in {"JSONBType", "JSONB", "JSON"}, (
            f"{json_col} must remain JSONB-family typed (got {json_type_name})."
        )


def test_string_lengths_unchanged():
    """Per-column VARCHAR length pinning — drift here changes writer
    contracts (e.g. truncation of ``block_reason_code`` enum values)."""
    cols = RiskDecision.__table__.columns
    for col_name, expected_len in EXPECTED_STRING_LENGTHS.items():
        actual_len = cols[col_name].type.length
        assert actual_len == expected_len, (
            f"RiskDecision.{col_name}.length drifted: expected "
            f"{expected_len}, got {actual_len}."
        )


def test_numeric_precision_unchanged():
    """Precision/scale on the two ``Numeric`` columns matter for risk
    accounting — drift here silently changes value rounding."""
    cols = RiskDecision.__table__.columns
    assert cols["position_risk_pct"].type.precision == 10
    assert cols["position_risk_pct"].type.scale == 4
    assert cols["notional_allowed"].type.precision == 18
    assert cols["notional_allowed"].type.scale == 8


def test_signal_id_foreign_key_to_signals_table():
    """``signal_id`` must keep its FK to ``signals.id``. Dropping the
    FK silently allows orphan risk decisions."""
    fks = RiskDecision.__table__.columns["signal_id"].foreign_keys
    fk_targets = {fk.target_fullname for fk in fks}
    assert "signals.id" in fk_targets, (
        f"RiskDecision.signal_id FK to signals.id missing. Found: {fk_targets}"
    )


def test_id_and_created_at_still_supplied_by_mixins():
    cols = RiskDecision.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in RiskDecision.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"
