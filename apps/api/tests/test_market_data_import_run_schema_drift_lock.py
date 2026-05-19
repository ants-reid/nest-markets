"""Cycle 44 — Schema drift-lock for ``market_data_import_runs``.

Locks the per-import-attempt audit row (MH-01 Data Centre; dependency
surface of MH-02 Historical Import Manager).

Pinned shape:
  * 14 business columns + nullability + String lengths
  * 3 indexed columns: batch_id, provider, asset_symbol
  * Numeric(10, 3) duration_seconds
  * **ANTI-ESCALATION**: ``status`` defaults to ``'pending'`` (Python).
    A silent flip to 'complete' would let an import row read as
    successful without an actual run.
  * Required identity fields (provider, asset_symbol, timeframe)
    carry no silent defaults.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Integer, Numeric, String, Text

from app.db.models.market_data_import_run import MarketDataImportRun


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "batch_id": (True, None, None),  # UUID
    "provider": (False, String, 100),
    "asset_symbol": (False, String, 50),
    "timeframe": (False, String, 10),
    "from_date": (True, DateTime, None),
    "to_date": (True, DateTime, None),
    "rows_requested": (True, Integer, None),
    "rows_upserted": (True, Integer, None),
    "rows_skipped": (True, Integer, None),
    "status": (False, String, 50),
    "error_message": (True, Text, None),
    "duration_seconds": (True, Numeric, None),
    "started_at": (True, DateTime, None),
    "finished_at": (True, DateTime, None),
}


INDEXED_COLUMNS: list[str] = ["batch_id", "provider", "asset_symbol"]


def test_table_name_unchanged():
    assert MarketDataImportRun.__tablename__ == "market_data_import_runs"


def test_business_column_set_unchanged():
    table_cols = set(MarketDataImportRun.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"MarketDataImportRun missing column(s): {sorted(missing)}."
    assert not extra, f"MarketDataImportRun has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MarketDataImportRun.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MarketDataImportRun.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = MarketDataImportRun.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"MarketDataImportRun.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = MarketDataImportRun.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"MarketDataImportRun.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_duration_seconds_precision_unchanged():
    col = MarketDataImportRun.__table__.columns["duration_seconds"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 10
    assert col.type.scale == 3


def test_indexed_columns_remain_indexed():
    for col_name in INDEXED_COLUMNS:
        col = MarketDataImportRun.__table__.columns[col_name]
        assert col.index is True, (
            f"MarketDataImportRun.{col_name} must remain indexed (index=True)."
        )


def test_status_anti_escalation_default():
    """ANTI-ESCALATION: a fresh import row must default to
    ``status='pending'``. A silent flip to 'complete' would let an
    import row read as successful without an actual run."""
    col = MarketDataImportRun.__table__.columns["status"]
    assert col.nullable is False
    assert col.default is not None, (
        "MarketDataImportRun.status lost its Python default — ANTI-ESCALATION DRIFT."
    )
    assert col.default.arg == "pending", (
        f"MarketDataImportRun.status default drifted: expected 'pending', "
        f"got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_required_identity_fields_have_no_silent_defaults():
    for col_name in ("provider", "asset_symbol", "timeframe"):
        col = MarketDataImportRun.__table__.columns[col_name]
        assert col.default is None, (
            f"MarketDataImportRun.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"MarketDataImportRun.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = MarketDataImportRun.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in MarketDataImportRun.__table__.primary_key.columns]
    assert pk_cols == ["id"]
