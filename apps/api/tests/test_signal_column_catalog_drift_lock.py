"""Drift-lock: Signal SQLAlchemy column catalog (cycle 72).

Pins the column names of the ``Signal`` ORM model — the upstream
record that RiskDecision attribution joins on. Renaming
``signal_status`` would silently break the dashboard's
should-trade filter.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.signal import Signal

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "asset_id",
        "catalyst_score",
        "catalyst_summary",
        "catalyst_type",
        "confidence",
        "created_at",
        "direction",
        "entry_max",
        "entry_min",
        "feature_snapshot_id",
        "horizon_label",
        "id",
        "invalidators_json",
        "model_version_id",
        "prompt_version_id",
        "provider_name",
        "raw_llm_json",
        "regime",
        "scan_ts",
        "setup_type",
        "signal_score",
        "signal_status",
        "stop_price",
        "target_price",
        "thesis",
        "timeframe",
    }
)

SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "asset_id",
        "direction",
        "stop_price",
        "target_price",
        "signal_status",
        "confidence",
        "scan_ts",
    }
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in Signal.__table__.columns)


def test_signal_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "Signal column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_signal_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"Signal missing safety/attribution column(s): {sorted(missing)}."
    )
