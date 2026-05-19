"""Drift-lock: BrokerSubmitDecision SQLA column catalog (cycle 73).

Pins the columns of the durable record that captures every
broker-submit *decision* (including would-block-but-was-not-armed
preflight outcomes). Renaming ``would_block`` would silently break
the dry-run safety telemetry.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.broker_submit_decision import BrokerSubmitDecision

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "blocked_reason_code",
        "blocked_reason_text",
        "created_at",
        "id",
        "intent",
        "preflight_json",
        "signal_id",
        "would_block",
    }
)
SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"id", "intent", "signal_id", "would_block", "blocked_reason_code",
     "preflight_json"}
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in BrokerSubmitDecision.__table__.columns)


def test_broker_submit_decision_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "BrokerSubmitDecision column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_broker_submit_decision_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"BrokerSubmitDecision missing safety column(s): "
        f"{sorted(missing)}."
    )
