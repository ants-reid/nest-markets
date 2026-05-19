"""Cycle 53 — Schema drift-lock for ``provider_asset_coverage`` (MH-02).

One row per (provider, asset_symbol, timeframe) tuple, upserted on each
import run. Distinct from ``provider_coverage_report`` (per-provider
aggregate snapshot).

Pinned shape:
  * 12 business columns.
  * UniqueConstraint ``uq_pac_provider_asset_tf`` on
    (provider, asset_symbol, timeframe) — anti-duplicate guard so
    repeat imports update the same row instead of producing fan-out.
    Drift here would silently bloat the table and break upsert logic.
  * ``approved_for_backtest`` Boolean NOT-NULL default False —
    SAFETY-RELEVANT: a NULL or True drift would silently allow a new
    provider's data to be backtested before any quality gating.
  * ``candle_count`` Integer NOT-NULL default 0 — anti-NULL guard.
  * ``last_import_run_id`` is a soft-FK UUID (no formal FK; nullable).

Drift-lock notes:
    * Pure additive test; no production code change.
    * Coverage rows are READ-ONLY for the trading path (consumed by the
      data-quality gating layer). The auto-trading gate
      ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.provider_asset_coverage import ProviderAssetCoverage


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "provider": (False, String, 100),
    "asset_symbol": (False, String, 50),
    "timeframe": (False, String, 10),
    "requested_start": (True, DateTime, None),
    "requested_end": (True, DateTime, None),
    "available_from": (True, DateTime, None),
    "available_to": (True, DateTime, None),
    "candle_count": (False, Integer, None),
    "missing_pct": (True, Float, None),
    "quality_score": (True, Float, None),
    "approved_for_backtest": (False, Boolean, None),
    "limitations": (True, Text, None),
    "last_import_run_id": (True, None, None),  # soft-FK UUID
    "evaluated_at": (True, DateTime, None),
}


def test_table_name_unchanged():
    assert ProviderAssetCoverage.__tablename__ == "provider_asset_coverage"


def test_business_column_set_unchanged():
    table_cols = set(ProviderAssetCoverage.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ProviderAssetCoverage missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ProviderAssetCoverage has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ProviderAssetCoverage.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ProviderAssetCoverage.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_pinned():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String:
            continue
        col = ProviderAssetCoverage.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"ProviderAssetCoverage.{col_name} String length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_unique_constraint_provider_asset_tf_unchanged():
    """Anti-duplicate guard: repeat imports must update, not fan out."""
    from sqlalchemy import UniqueConstraint
    uniques = [
        c for c in ProviderAssetCoverage.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    by_name = {u.name: u for u in uniques if u.name}
    assert "uq_pac_provider_asset_tf" in by_name, (
        f"ProviderAssetCoverage UQ uq_pac_provider_asset_tf missing. "
        f"Found: {sorted(by_name.keys())}."
    )
    uq = by_name["uq_pac_provider_asset_tf"]
    cols = [c.name for c in uq.columns]
    assert cols == ["provider", "asset_symbol", "timeframe"], (
        f"ProviderAssetCoverage UQ column order drifted: "
        f"expected ['provider', 'asset_symbol', 'timeframe'], got {cols}."
    )


def test_approved_for_backtest_default_false_safety_guard():
    """SAFETY: new provider data must default to NOT approved for backtest."""
    col = ProviderAssetCoverage.__table__.columns["approved_for_backtest"]
    assert isinstance(col.type, Boolean)
    assert col.default is not None, (
        "ProviderAssetCoverage.approved_for_backtest must have a Python-side "
        "default to prevent NULL being treated as approved."
    )
    default_value = col.default.arg
    if callable(default_value):
        default_value = default_value({})
    assert default_value is False, (
        f"ProviderAssetCoverage.approved_for_backtest default drifted: "
        f"expected False, got {default_value!r}. SAFETY-RELEVANT — drift "
        "would silently allow new providers to be backtested before quality gating."
    )


def test_candle_count_default_zero():
    col = ProviderAssetCoverage.__table__.columns["candle_count"]
    assert isinstance(col.type, Integer)
    assert col.default is not None
    default_value = col.default.arg
    if callable(default_value):
        default_value = default_value({})
    assert default_value == 0, (
        f"ProviderAssetCoverage.candle_count default drifted: "
        f"expected 0, got {default_value!r}."
    )


def test_last_import_run_id_is_soft_reference():
    col = ProviderAssetCoverage.__table__.columns["last_import_run_id"]
    assert isinstance(col.type, UUID)
    assert len(list(col.foreign_keys)) == 0, (
        "ProviderAssetCoverage.last_import_run_id unexpectedly has FK; "
        "soft-reference pattern required (cascade-deleting import runs "
        "must not wipe coverage history)."
    )


def test_provider_and_asset_symbol_are_indexed():
    """Both are filter targets in dashboard queries."""
    for col_name in ("provider", "asset_symbol"):
        col = ProviderAssetCoverage.__table__.columns[col_name]
        assert col.index is True, (
            f"ProviderAssetCoverage.{col_name}.index drifted: expected True."
        )


def test_datetime_columns_are_timezone_aware():
    for col_name in (
        "requested_start", "requested_end", "available_from",
        "available_to", "evaluated_at",
    ):
        col = ProviderAssetCoverage.__table__.columns[col_name]
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True, (
            f"ProviderAssetCoverage.{col_name}.timezone drifted: expected True."
        )
