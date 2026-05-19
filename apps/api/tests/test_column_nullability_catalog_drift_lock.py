"""Drift-lock: pin the NOT NULL columns on safety-critical tables.

Cycle 59 — MH-DRIFTLOCK-COLUMN-NULLABILITY-CATALOG (pure additive
test-only).

Why
---
Cycle 56 pinned Boolean defaults; cycle 57 pinned FK ondelete; cycle 58
pinned routes/audit shapes/conftest. None of those would catch a silent
loosening of a NOT NULL column on a safety-critical table — e.g.
``risk_decisions.approved`` becoming nullable would mean the audit log
could record decisions whose outcome is undetermined, breaking safety
attribution.

This file pins, for each safety-critical table, the *exact set of
NOT NULL column names* (i.e. ``nullable=False``). Both directions are
checked: a NOT NULL column becoming NULL fails the test, and a NULL
column becoming NOT NULL also fails (forces deliberation in case the
upgrade was unintentional).

A subset ``SAFETY_REQUIRED_NOT_NULL`` lists columns whose NOT NULL
posture is a hard safety contract (intent on broker_submit_decisions,
approved on risk_decisions, etc.).

Drift-lock guarantees
---------------------
* Read-only — no DB connection, no migration. Reads ORM metadata only.
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from app.db import models as _models  # noqa: F401  (side-effect: register tables)
from app.db.base import Base


# Pinned NOT NULL column sets per safety-critical table, captured at
# cycle 59. Each value is the set of column names where nullable=False.
EXPECTED_NOT_NULL: dict[str, set[str]] = {
    "broker_submit_decisions": {
        "intent",
        "would_block",
        "id",
        "created_at",
    },
    "broker_trade_events": {
        "broker_provider",
        "source",
        "event_fingerprint",
        "id",
        "created_at",
    },
    "execution_modes": {
        "name",
        "is_active",
        "requires_approval",
        "allows_live_orders",
        "id",
        "created_at",
    },
    "news_in_decision_log": {
        "decision_kind",
        "evidence_class",
        "id",
        "created_at",
    },
    "positions": {
        "asset_id",
        "status",
        "side",
        "opened_by",
        "id",
        "created_at",
        "updated_at",
    },
    "risk_decisions": {
        "approved",
        "id",
        "created_at",
    },
    "risk_profiles": {
        "name",
        "is_active",
        "auto_trade_enabled",
        "confirm_before_trade_enabled",
        "kill_switch_enabled",
        "id",
        "created_at",
        "updated_at",
    },
    "signals": {
        "asset_id",
        "scan_ts",
        "timeframe",
        "signal_status",
        "direction",
        "setup_type",
        "id",
        "created_at",
    },
    "trading_control_arming_states": {
        "scope",
        "trading_mode",
        "state",
        "id",
        "created_at",
        "updated_at",
    },
}


# Safety-required NOT NULL columns: removing nullable=False on any of
# these would silently allow ambiguous safety-attribution rows.
# Format: (table, column).
SAFETY_REQUIRED_NOT_NULL: set[tuple[str, str]] = {
    # broker submit gate must always know its intent and gate decision
    ("broker_submit_decisions", "intent"),
    ("broker_submit_decisions", "would_block"),
    # risk audit must always know whether the decision was approved
    ("risk_decisions", "approved"),
    # news-in-decision-log must always identify the decision kind +
    # evidence class
    ("news_in_decision_log", "decision_kind"),
    ("news_in_decision_log", "evidence_class"),
    # trading_control_arming_states is the durable arming record
    ("trading_control_arming_states", "scope"),
    ("trading_control_arming_states", "trading_mode"),
    ("trading_control_arming_states", "state"),
    # execution_modes drives live-vs-paper resolution
    ("execution_modes", "name"),
    ("execution_modes", "is_active"),
    ("execution_modes", "allows_live_orders"),
    # risk_profiles drives auto-trading + kill-switch posture
    ("risk_profiles", "auto_trade_enabled"),
    ("risk_profiles", "kill_switch_enabled"),
    # broker_trade_events fingerprint is the dedup guard for trades
    ("broker_trade_events", "event_fingerprint"),
    ("broker_trade_events", "broker_provider"),
    ("broker_trade_events", "source"),
    # signals always require asset, timestamp, status
    ("signals", "asset_id"),
    ("signals", "scan_ts"),
    ("signals", "signal_status"),
    ("signals", "direction"),
    # positions always require asset and side
    ("positions", "asset_id"),
    ("positions", "status"),
    ("positions", "side"),
    ("positions", "opened_by"),
}


def _collect_not_null_columns(table_name: str) -> set[str]:
    table = Base.metadata.tables.get(table_name)
    assert table is not None, (
        f"Safety-critical table '{table_name}' not present in ORM "
        "metadata. Was the table renamed without updating "
        "tests/test_column_nullability_catalog_drift_lock.py?"
    )
    return {c.name for c in table.columns if not c.nullable}


def test_safety_critical_table_not_null_catalog_exact_match() -> None:
    drift: list[tuple[str, set[str], set[str]]] = []
    for table_name, expected in EXPECTED_NOT_NULL.items():
        actual = _collect_not_null_columns(table_name)
        missing = expected - actual  # NOT NULL relaxed to NULL
        extra = actual - expected    # NULL tightened to NOT NULL
        if missing or extra:
            drift.append((table_name, missing, extra))
    assert not drift, (
        "NOT NULL column-set drift on safety-critical table(s). For "
        "each: 'missing' means a NOT NULL column was relaxed to NULL "
        "(SAFETY-CRITICAL drift); 'extra' means a previously-NULL "
        "column was tightened to NOT NULL (review needed). Drift: "
        f"{drift}. Update EXPECTED_NOT_NULL and append a build-ledger "
        "entry."
    )


def test_safety_required_not_null_columns_remain_not_null() -> None:
    offenders: list[tuple[str, str]] = []
    for table_name, column_name in SAFETY_REQUIRED_NOT_NULL:
        not_null = _collect_not_null_columns(table_name)
        if column_name not in not_null:
            offenders.append((table_name, column_name))
    assert not offenders, (
        "SAFETY-required NOT NULL columns silently relaxed to NULL: "
        f"{offenders}. These columns underpin trading-decision audit "
        "attribution, broker dedup, or auto/live trading enablement. "
        "Reverse the relaxation or perform a deliberate, ledger-"
        "tracked migration accompanied by an explicit drift-lock "
        "review (auto-paper / auto / live trading must remain OFF)."
    )


def test_safety_critical_tables_present() -> None:
    """Sanity floor: every safety-critical table must still exist."""
    missing: list[str] = []
    for table_name in EXPECTED_NOT_NULL.keys():
        if Base.metadata.tables.get(table_name) is None:
            missing.append(table_name)
    assert not missing, (
        f"Safety-critical table(s) silently removed from ORM metadata: "
        f"{missing}. These tables back the audit / arming / risk / "
        "broker safety surfaces; their removal must be a deliberate "
        "ledger-tracked migration."
    )
