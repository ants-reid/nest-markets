"""Cycle 44 — Schema drift-lock for ``market_data_gaps``.

Locks the detected-gap record table for (asset_symbol, timeframe).

Pinned shape:
  * 9 business columns + nullability + String lengths
  * asset_symbol indexed
  * gap_start / gap_end NOT NULL (a gap without bounds is meaningless)
  * **ANTI-ESCALATION**: ``status`` defaults to ``'open'`` and
    ``severity`` defaults to ``'low'`` at the Python layer — but
    expected_candles_missing defaults to 1 (not 0) so a row written
    without a measured count still records that *something* is missing.
  * Required identity fields (asset_symbol, timeframe, gap_start,
    gap_end) carry no silent defaults.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Note: a default ``status='resolved'`` would silently make
      every newly-detected gap disappear from operator dashboards.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, Text

from app.db.models.market_data_gap import MarketDataGap


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "asset_symbol": (False, String, 50),
    "timeframe": (False, String, 10),
    "provider": (True, String, 100),
    "gap_start": (False, DateTime, None),
    "gap_end": (False, DateTime, None),
    "expected_candles_missing": (False, Integer, None),
    "severity": (False, String, 20),
    "status": (False, String, 50),
    "import_run_id": (True, None, None),  # UUID
    "notes": (True, Text, None),
}


def test_table_name_unchanged():
    assert MarketDataGap.__tablename__ == "market_data_gaps"


def test_business_column_set_unchanged():
    table_cols = set(MarketDataGap.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"MarketDataGap missing column(s): {sorted(missing)}."
    assert not extra, f"MarketDataGap has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MarketDataGap.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MarketDataGap.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = MarketDataGap.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"MarketDataGap.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = MarketDataGap.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"MarketDataGap.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_asset_symbol_indexed():
    col = MarketDataGap.__table__.columns["asset_symbol"]
    assert col.index is True, (
        "MarketDataGap.asset_symbol must remain indexed."
    )


def test_status_anti_escalation_default():
    """ANTI-ESCALATION: a freshly-detected gap row must default to
    ``status='open'``. A silent flip to 'resolved' would make every
    newly-detected gap disappear from operator dashboards."""
    col = MarketDataGap.__table__.columns["status"]
    assert col.default is not None, (
        "MarketDataGap.status lost its Python default — ANTI-ESCALATION DRIFT."
    )
    assert col.default.arg == "open", (
        f"MarketDataGap.status default drifted: expected 'open', "
        f"got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_severity_default_low():
    col = MarketDataGap.__table__.columns["severity"]
    assert col.default is not None
    assert col.default.arg == "low", (
        f"MarketDataGap.severity default drifted: expected 'low', "
        f"got {col.default.arg!r}."
    )


def test_expected_candles_missing_default_one():
    """expected_candles_missing must default to 1 (not 0) so a row
    written without a measured count still records that *something*
    is missing."""
    col = MarketDataGap.__table__.columns["expected_candles_missing"]
    assert col.default is not None
    assert col.default.arg == 1, (
        f"MarketDataGap.expected_candles_missing default drifted: "
        f"expected 1, got {col.default.arg!r}."
    )


def test_required_identity_fields_have_no_silent_defaults():
    for col_name in ("asset_symbol", "timeframe", "gap_start", "gap_end"):
        col = MarketDataGap.__table__.columns[col_name]
        assert col.default is None, (
            f"MarketDataGap.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"MarketDataGap.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = MarketDataGap.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in MarketDataGap.__table__.primary_key.columns]
    assert pk_cols == ["id"]
