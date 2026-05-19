"""Drift-lock: RiskDecision SQLAlchemy column catalog (cycle 71).

Pins the column names of the ``RiskDecision`` ORM model — the table
that records WHY a signal was approved or blocked. Renaming
``approved`` to ``status`` would silently break every audit /
attribution query.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.risk_decision import RiskDecision

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "approved",
        "block_reason_code",
        "blocked_reasons_json",
        "blocking_rule",
        "cooldown_ok",
        "correlation_bucket",
        "created_at",
        "decision_json",
        "drawdown_ok",
        "id",
        "kill_switch_active",
        "notional_allowed",
        "position_risk_pct",
        "risk_profile_id",
        "session_ok",
        "signal_id",
        "spread_ok",
        "timestamp",
    }
)

SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "approved",
        "blocked_reasons_json",
        "kill_switch_active",
        "signal_id",
        "risk_profile_id",
        "timestamp",
    }
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in RiskDecision.__table__.columns)


def test_risk_decision_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "RiskDecision column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration and update "
        "EXPECTED_COLUMNS."
    )


def test_risk_decision_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"RiskDecision missing safety-attribution column(s): "
        f"{sorted(missing)}."
    )
