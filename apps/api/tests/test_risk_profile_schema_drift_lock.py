"""Cycle 39 — Schema drift-lock for ``risk_profiles``.

FK target of ``risk_decisions.risk_profile_id`` (MH-153-A). Most
important invariants are the **three anti-escalation defaults** that
guarantee a freshly-seeded risk profile is safe by default:

  * ``auto_trade_enabled = False``  — auto trading off by default
  * ``confirm_before_trade_enabled = True``  — manual confirm required
  * ``kill_switch_enabled = True``  — kill switch on by default

Plus ``is_active = 'inactive'`` (a new profile is not active until
explicitly activated) and the UNIQUE constraint on ``name``.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection only.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Numeric, String

from app.db.models.risk_profile import RiskProfile


EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "name": (False, String, 255),
    "is_active": (False, String, 20),
    "max_capital_allocated": (True, Numeric, None),
    "max_risk_per_trade_pct": (True, Numeric, None),
    "max_daily_drawdown_pct": (True, Numeric, None),
    "max_open_positions": (True, Numeric, None),
    "max_correlated_positions": (True, Numeric, None),
    "max_correlated_bucket_exposure": (True, Numeric, None),
    "min_confidence": (True, Numeric, None),
    "min_signal_score": (True, Numeric, None),
    "max_spread_bps_fx": (True, Numeric, None),
    "max_spread_bps_equity": (True, Numeric, None),
    "cooldown_after_3_losses_min": (True, Numeric, None),
    "auto_trade_enabled": (False, Boolean, None),
    "confirm_before_trade_enabled": (False, Boolean, None),
    "kill_switch_enabled": (False, Boolean, None),
}


# (column, expected_python_default, expected_server_default_substring_lower)
ANTI_ESCALATION_DEFAULTS: list[tuple[str, object, str]] = [
    ("auto_trade_enabled", False, "false"),
    ("confirm_before_trade_enabled", True, "true"),
    ("kill_switch_enabled", True, "true"),
]


def test_table_name_unchanged():
    assert RiskProfile.__tablename__ == "risk_profiles"


def test_business_column_set_unchanged():
    table_cols = set(RiskProfile.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"RiskProfile is missing column(s): {sorted(missing)}."
    assert not extra, f"RiskProfile has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = RiskProfile.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"RiskProfile.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = RiskProfile.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"RiskProfile.{col_name} length drifted: expected "
            f"{expected_len}, got {col.type.length}."
        )


def test_name_is_unique():
    col = RiskProfile.__table__.columns["name"]
    assert col.unique is True, "RiskProfile.name must remain UNIQUE."


def test_is_active_default_is_inactive():
    """A new risk profile must default to 'inactive' so it is not
    immediately picked up by any active-profile selector."""
    col = RiskProfile.__table__.columns["is_active"]
    assert col.default is not None
    assert col.default.arg == "inactive", (
        f"RiskProfile.is_active Python default drifted: expected "
        f"'inactive', got {col.default.arg!r}."
    )
    assert col.server_default is not None
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "inactive" in str(server_default_value), (
        f"RiskProfile.is_active server_default drifted: expected "
        f"'inactive', got {server_default_value!r}."
    )


def test_anti_escalation_defaults():
    """The three Boolean safety defaults (auto_trade_enabled=False,
    confirm_before_trade_enabled=True, kill_switch_enabled=True) must
    remain. ANY of these flipping silently is an anti-escalation
    breach."""
    for col_name, expected_python, expected_server_substr in ANTI_ESCALATION_DEFAULTS:
        col = RiskProfile.__table__.columns[col_name]
        assert col.default is not None, (
            f"RiskProfile.{col_name} must keep its Python default — "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.default.arg is expected_python, (
            f"RiskProfile.{col_name} Python default drifted: expected "
            f"{expected_python}, got {col.default.arg!r}. "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.server_default is not None, (
            f"RiskProfile.{col_name} must keep its server_default — "
            "ANTI-ESCALATION DRIFT."
        )
        server_default_value = col.server_default.arg
        if hasattr(server_default_value, "text"):
            server_default_value = server_default_value.text
        assert expected_server_substr in str(server_default_value).lower(), (
            f"RiskProfile.{col_name} server_default drifted: expected "
            f"{expected_server_substr!r}, got {server_default_value!r}. "
            "ANTI-ESCALATION DRIFT."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = RiskProfile.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in RiskProfile.__table__.primary_key.columns]
    assert pk_cols == ["id"]
