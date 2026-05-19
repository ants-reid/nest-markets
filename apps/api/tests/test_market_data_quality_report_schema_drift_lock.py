"""Cycle 44 — Schema drift-lock for ``market_data_quality_reports``.

Locks the per-(asset, timeframe) bar-quality snapshot table — parent
of the cycle-43 ``quality_review_audits`` CASCADE-FK.

Pinned shape:
  * 22 business columns + nullability + String lengths
  * Counter columns default to 0 (no silent "always good"/"never bad")
  * ``metadata_json`` JSONB-family
  * **ANTI-ESCALATION**: ``approved_for_backtest`` defaults to
    ``False`` (a silent True would let raw bars be auto-approved
    for backtests and downstream model training)
  * **ANTI-ESCALATION**: ``review_status`` defaults to
    ``'unreviewed'`` at BOTH Python and server_default layers (a
    silent flip to 'reviewed'/'approved' would let an MH-13 triage
    item disappear without operator action)

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text

from app.db.models.market_data_quality_report import MarketDataQualityReport


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "asset_symbol": (False, String, 50),
    "timeframe": (False, String, 10),
    "provider": (True, String, 100),
    "evaluated_at": (False, DateTime, None),
    "expected_bars": (True, Integer, None),
    "actual_bars": (False, Integer, None),
    "total_bars": (False, Integer, None),
    "completeness_pct": (True, Float, None),
    "missing_bars": (False, Integer, None),
    "duplicate_bars": (False, Integer, None),
    "bad_price_bars": (False, Integer, None),
    "suspicious_spike_bars": (False, Integer, None),
    "stale_bars": (False, Integer, None),
    "earliest_bar_ts": (True, DateTime, None),
    "latest_bar_ts": (True, DateTime, None),
    "notes": (True, Text, None),
    "quality_score": (True, Float, None),
    "approved_for_backtest": (False, Boolean, None),
    "metadata_json": (True, None, None),  # JSONB
    "review_status": (False, String, 50),
    "review_notes": (True, Text, None),
    "reviewed_by": (True, String, 255),
    "reviewed_at": (True, DateTime, None),
}


COUNTERS_DEFAULT_ZERO: list[str] = [
    "actual_bars",
    "total_bars",
    "missing_bars",
    "duplicate_bars",
    "bad_price_bars",
    "suspicious_spike_bars",
    "stale_bars",
]


def test_table_name_unchanged():
    assert MarketDataQualityReport.__tablename__ == "market_data_quality_reports"


def test_business_column_set_unchanged():
    table_cols = set(MarketDataQualityReport.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"MarketDataQualityReport missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"MarketDataQualityReport has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MarketDataQualityReport.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MarketDataQualityReport.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = MarketDataQualityReport.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"MarketDataQualityReport.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = MarketDataQualityReport.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"MarketDataQualityReport.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_asset_symbol_indexed():
    col = MarketDataQualityReport.__table__.columns["asset_symbol"]
    assert col.index is True, (
        "MarketDataQualityReport.asset_symbol must remain indexed."
    )


def test_metadata_json_is_jsonb_family():
    col = MarketDataQualityReport.__table__.columns["metadata_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES, (
        f"MarketDataQualityReport.metadata_json must remain JSONB-family; "
        f"got {type_name}."
    )


def test_counters_default_to_zero():
    """Every counter column must default to 0 — drift here would let
    quality reports silently look "all good" or "all bad" with no
    actual measurement."""
    for col_name in COUNTERS_DEFAULT_ZERO:
        col = MarketDataQualityReport.__table__.columns[col_name]
        assert col.default is not None, (
            f"MarketDataQualityReport.{col_name} lost its Python default."
        )
        assert col.default.arg == 0, (
            f"MarketDataQualityReport.{col_name} default drifted: "
            f"expected 0, got {col.default.arg!r}."
        )


def test_approved_for_backtest_anti_escalation_default():
    """ANTI-ESCALATION: a fresh quality-report row must default to
    ``approved_for_backtest=False``. A silent True would let raw
    bars be auto-approved for backtests and downstream model training.
    """
    col = MarketDataQualityReport.__table__.columns["approved_for_backtest"]
    assert col.nullable is False
    assert col.default is not None, (
        "MarketDataQualityReport.approved_for_backtest lost its default — "
        "ANTI-ESCALATION DRIFT."
    )
    assert col.default.arg is False, (
        f"MarketDataQualityReport.approved_for_backtest default drifted: "
        f"expected False, got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_review_status_anti_escalation_default():
    """ANTI-ESCALATION: ``review_status`` must default to
    ``'unreviewed'`` at BOTH Python and server_default layers. A
    silent flip to 'reviewed'/'approved' would let an MH-13 triage
    item disappear without operator action."""
    col = MarketDataQualityReport.__table__.columns["review_status"]
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg == "unreviewed", (
        f"MarketDataQualityReport.review_status Python default drifted: "
        f"expected 'unreviewed', got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )
    assert col.server_default is not None, (
        "MarketDataQualityReport.review_status lost its server_default — "
        "ANTI-ESCALATION DRIFT."
    )
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "unreviewed" in str(server_default_value), (
        f"MarketDataQualityReport.review_status server_default drifted: "
        f"got {server_default_value!r}. ANTI-ESCALATION DRIFT."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = MarketDataQualityReport.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in MarketDataQualityReport.__table__.primary_key.columns]
    assert pk_cols == ["id"]
