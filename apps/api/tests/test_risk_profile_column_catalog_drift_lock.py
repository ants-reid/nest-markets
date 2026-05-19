"""Drift-lock: RiskProfile SQLAlchemy column catalog (cycle 72).

Pins the column names of the ``RiskProfile`` ORM model — the row
that drives every per-trade risk gate. Renaming
``auto_trade_enabled`` or ``kill_switch_enabled`` would silently
disable the corresponding safety check.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.risk_profile import RiskProfile

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "auto_trade_enabled",
        "confirm_before_trade_enabled",
        "cooldown_after_3_losses_min",
        "created_at",
        "id",
        "is_active",
        "kill_switch_enabled",
        "max_capital_allocated",
        "max_correlated_bucket_exposure",
        "max_correlated_positions",
        "max_daily_drawdown_pct",
        "max_open_positions",
        "max_risk_per_trade_pct",
        "max_spread_bps_equity",
        "max_spread_bps_fx",
        "min_confidence",
        "min_signal_score",
        "name",
        "updated_at",
    }
)

SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "is_active",
        "auto_trade_enabled",
        "kill_switch_enabled",
        "confirm_before_trade_enabled",
        "max_risk_per_trade_pct",
        "max_daily_drawdown_pct",
        "max_open_positions",
    }
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in RiskProfile.__table__.columns)


def test_risk_profile_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "RiskProfile column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_risk_profile_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"RiskProfile missing safety column(s): {sorted(missing)}. "
        "These columns drive the per-trade risk gates and kill switch."
    )
