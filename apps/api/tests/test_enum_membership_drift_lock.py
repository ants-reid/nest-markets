"""Cycle 54 — Cross-service enum membership pin.

Pins the **member set** (not the source-code order) of every enum that
participates in routing, broker submission, position lifecycle, or
regime classification. Drift in any of these silently changes routing
behaviour because string-equality and DB CHECK constraints depend on
the exact value strings.

This is a **safety contract pin**, not a feature test:
  * Adding a member is a NEW BUSINESS CASE that requires a deliberate
    update here AND a migration if the enum has a PG enum type.
  * Removing or renaming a member would silently cause every existing
    DB row with that value to fail enum validation on read.
  * Changing the wire-string value of an existing member would silently
    break every dashboard, every audit query, and every CHECK constraint.

Drift-lock notes:
    * Pure additive test; no production code change.
    * The auto-trading gate ``assert_auto_trading_allowed()`` is
      unchanged. This pin only documents the existing enum contract.
"""

from __future__ import annotations

from app.db.enums import (
    AssetClass,
    ExecutionModeName,
    ExecutionOutcomeStatus,
    MarketRegimeType,
    OrderStatus,
    PositionStatus,
    SignalStatus,
    TradeDirection,
)


# ── AssetClass ──────────────────────────────────────────────────────────
# Note: NO "STOCK" member; equity-class assets use EQUITY. Drift to
# add STOCK silently bypasses the equity-vs-etf routing split.
EXPECTED_ASSET_CLASS: dict[str, str] = {
    "FX": "fx",
    "EQUITY": "equity",
    "ETF": "etf",
    "INDEX_PROXY": "index_proxy",
    "COMMODITY_PROXY": "commodity_proxy",
    "CRYPTO": "crypto",
}


# ── OrderStatus ─────────────────────────────────────────────────────────
EXPECTED_ORDER_STATUS: dict[str, str] = {
    "PENDING": "pending",
    "NEW": "new",
    "ACCEPTED": "accepted",
    "FILLED": "filled",
    "CANCELED": "canceled",  # American spelling pinned (broker convention)
    "REJECTED": "rejected",
    "CLOSED": "closed",
}


# ── PositionStatus ──────────────────────────────────────────────────────
EXPECTED_POSITION_STATUS: dict[str, str] = {
    "OPEN": "open",
    "CLOSED": "closed",
}


# ── ExecutionModeName ───────────────────────────────────────────────────
# SAFETY-RELEVANT: AUTO_PAPER, AUTO_LIVE, CONFIRM_LIVE wire strings are
# read by trading_control gating. Drift in any value silently changes
# how the safety gate interprets the active mode.
EXPECTED_EXECUTION_MODE_NAME: dict[str, str] = {
    "PAPER": "paper",
    "AUTO_PAPER": "auto_paper",
    "AUTO_LIVE": "auto_live",
    "CONFIRM_LIVE": "confirm_live",
    "PENDING_APPROVAL": "pending_approval",
}


# ── MarketRegimeType ────────────────────────────────────────────────────
# 6-member contract pinned by cycle-50 model lock; this is the wire-value
# pin (model lock pinned membership only).
EXPECTED_MARKET_REGIME_TYPE: dict[str, str] = {
    "RISK_ON": "risk_on",
    "RISK_OFF": "risk_off",
    "HIGH_VOL": "high_vol",
    "LOW_VOL": "low_vol",
    "CHOP": "chop",
    "TREND": "trend",
}


# ── ExecutionOutcomeStatus ──────────────────────────────────────────────
EXPECTED_EXECUTION_OUTCOME_STATUS: dict[str, str] = {
    "EXECUTED": "executed",
    "BLOCKED": "blocked",
    "MISSED": "missed",
    "SKIPPED": "skipped",
}


# ── TradeDirection ──────────────────────────────────────────────────────
EXPECTED_TRADE_DIRECTION: dict[str, str] = {
    "LONG": "long",
    "SHORT": "short",
    "FLAT": "flat",
}


# ── SignalStatus ────────────────────────────────────────────────────────
# 12-member lifecycle. Drift here silently breaks dashboards, alerts,
# and the signal pipeline state machine.
EXPECTED_SIGNAL_STATUS: dict[str, str] = {
    "CANDIDATE": "candidate",
    "RISK_APPROVED": "risk_approved",
    "RISK_BLOCKED": "risk_blocked",
    "PENDING_USER_APPROVAL": "pending_user_approval",
    "USER_APPROVED": "user_approved",
    "USER_REJECTED": "user_rejected",
    "PAPER_SUBMITTED": "paper_submitted",
    "PAPER_FILLED": "paper_filled",
    "LIVE_SUBMITTED": "live_submitted",
    "LIVE_FILLED": "live_filled",
    "CLOSED": "closed",
    "EXPIRED": "expired",
}


def _check_enum(enum_cls, expected: dict[str, str]) -> None:
    actual = {m.name: m.value for m in enum_cls}
    missing = set(expected) - set(actual)
    extra = set(actual) - set(expected)
    assert not missing, (
        f"{enum_cls.__name__} missing pinned member(s): {sorted(missing)}. "
        "Removing/renaming an enum member is breaking — every existing "
        "DB row with that value will fail enum validation on read."
    )
    assert not extra, (
        f"{enum_cls.__name__} has unexpected new member(s): {sorted(extra)}. "
        "Adding a member is a new business case that requires a deliberate "
        "update to this pin AND a migration if the enum has a PG type."
    )
    for name, expected_value in expected.items():
        assert actual[name] == expected_value, (
            f"{enum_cls.__name__}.{name} wire-value drifted: "
            f"expected {expected_value!r}, got {actual[name]!r}. "
            "Drift in wire value silently breaks every dashboard, audit "
            "query, and DB CHECK constraint that uses this string."
        )


def test_asset_class_membership_unchanged():
    _check_enum(AssetClass, EXPECTED_ASSET_CLASS)


def test_order_status_membership_unchanged():
    _check_enum(OrderStatus, EXPECTED_ORDER_STATUS)


def test_position_status_membership_unchanged():
    _check_enum(PositionStatus, EXPECTED_POSITION_STATUS)


def test_execution_mode_name_membership_unchanged():
    _check_enum(ExecutionModeName, EXPECTED_EXECUTION_MODE_NAME)


def test_market_regime_type_membership_unchanged():
    _check_enum(MarketRegimeType, EXPECTED_MARKET_REGIME_TYPE)


def test_execution_outcome_status_membership_unchanged():
    _check_enum(ExecutionOutcomeStatus, EXPECTED_EXECUTION_OUTCOME_STATUS)


def test_trade_direction_membership_unchanged():
    _check_enum(TradeDirection, EXPECTED_TRADE_DIRECTION)


def test_signal_status_membership_unchanged():
    _check_enum(SignalStatus, EXPECTED_SIGNAL_STATUS)


def test_no_stock_member_in_asset_class():
    """Explicit anti-drift guard: STOCK has been deliberately rejected
    in favour of EQUITY. A future contributor adding STOCK would silently
    bypass equity-vs-etf routing logic."""
    assert "STOCK" not in {m.name for m in AssetClass}, (
        "AssetClass.STOCK reintroduced. Use EQUITY instead — the routing "
        "layer assumes equity-class assets use AssetClass.EQUITY."
    )
