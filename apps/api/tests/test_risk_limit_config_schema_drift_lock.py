"""Cycle 40 — Schema drift-lock for ``risk_limit_configs``.

Locks the configurable risk-limit table that drives future
trading-control enforcement (max order notional, daily loss caps,
exposure caps, etc.).

Critical anti-escalation guarantees pinned here:
  * ``trading_mode`` defaults to ``'paper'`` at both Python and
    server_default layers — a freshly seeded risk-limit row applies
    to PAPER, not LIVE. A silent flip to ``'live'`` here would let an
    operator accidentally configure a live-trading limit when they
    intended a paper-trading limit.
  * ``scope`` defaults to ``'global'`` — widest, safest scope.
  * ``is_active`` defaults to ``True`` (pinned baseline; new limits
    are immediately in force as a safety property — limits are
    fail-closed, so they ON by default is the safe direction).
  * Numeric precision pinned at ``(18,8)`` for amount fields and
    ``(10,4)`` for percent fields so currency/percent semantics
    cannot drift silently.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, Numeric, String, Text

from app.db.models.risk_limit_config import RiskLimitConfig


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "scope": (False, String, 50),
    "trading_mode": (False, String, 20),
    "max_order_notional": (True, Numeric, None),
    "daily_loss_limit_amount": (True, Numeric, None),
    "daily_loss_limit_pct": (True, Numeric, None),
    "max_open_positions": (True, Integer, None),
    "max_total_exposure": (True, Numeric, None),
    "max_symbol_exposure": (True, Numeric, None),
    "max_trades_per_day": (True, Integer, None),
    "min_cash_buffer": (True, Numeric, None),
    "is_active": (False, Boolean, None),
    "notes": (True, Text, None),
}


# (column, expected precision, expected scale)
PINNED_NUMERIC_PRECISION: list[tuple[str, int, int]] = [
    ("max_order_notional", 18, 8),
    ("daily_loss_limit_amount", 18, 8),
    ("daily_loss_limit_pct", 10, 4),
    ("max_total_exposure", 18, 8),
    ("max_symbol_exposure", 18, 8),
    ("min_cash_buffer", 18, 8),
]


# (column, expected python default, expected server_default substring lower-cased)
PINNED_DEFAULTS: list[tuple[str, object, str]] = [
    ("trading_mode", "paper", "paper"),
    ("scope", "global", "global"),
    ("is_active", True, "true"),
]


def test_table_name_unchanged():
    assert RiskLimitConfig.__tablename__ == "risk_limit_configs"


def test_business_column_set_unchanged():
    table_cols = set(RiskLimitConfig.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"RiskLimitConfig missing column(s): {sorted(missing)}."
    assert not extra, (
        f"RiskLimitConfig has unexpected new column(s): {sorted(extra)}. "
        "Adding columns to a safety-config table requires an explicit "
        "phase + ledger entry."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = RiskLimitConfig.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"RiskLimitConfig.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = RiskLimitConfig.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"RiskLimitConfig.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = RiskLimitConfig.__table__.columns[col_name]
        assert col.type.length == expected_len, (
            f"RiskLimitConfig.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_precision_unchanged():
    for col_name, expected_precision, expected_scale in PINNED_NUMERIC_PRECISION:
        col = RiskLimitConfig.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision, (
            f"RiskLimitConfig.{col_name} precision drifted: "
            f"expected {expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"RiskLimitConfig.{col_name} scale drifted: "
            f"expected {expected_scale}, got {col.type.scale}."
        )


def test_anti_escalation_defaults():
    """ANTI-ESCALATION GUARANTEE — pinned defaults:
      * trading_mode='paper' (silent flip to 'live' would mis-target a
        risk-limit row from paper to live trading)
      * scope='global' (widest, safest scope)
      * is_active=True (limits are fail-closed; ON by default is the
        safe direction for risk caps)
    """
    for col_name, expected_python, expected_server_substr in PINNED_DEFAULTS:
        col = RiskLimitConfig.__table__.columns[col_name]
        assert col.default is not None, (
            f"RiskLimitConfig.{col_name} lost its Python default — "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.default.arg == expected_python, (
            f"RiskLimitConfig.{col_name} Python default drifted: "
            f"expected {expected_python!r}, got {col.default.arg!r}. "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.server_default is not None
        server_default_value = col.server_default.arg
        if hasattr(server_default_value, "text"):
            server_default_value = server_default_value.text
        assert expected_server_substr in str(server_default_value).lower(), (
            f"RiskLimitConfig.{col_name} server_default drifted: "
            f"expected substring {expected_server_substr!r}, "
            f"got {server_default_value!r}. ANTI-ESCALATION DRIFT."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = RiskLimitConfig.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in RiskLimitConfig.__table__.primary_key.columns]
    assert pk_cols == ["id"]
