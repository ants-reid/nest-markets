"""Cycle 53 — Schema drift-lock for ``mock_trades``.

Individual simulated trade recorded by the replay engine (MH-07+).

Pinned shape:
  * 17 business columns. Soft-FK UUIDs (backtest_run_id NOT-NULL,
    strategy_config_id nullable) — cycle-49+ soft-reference pattern.
  * ``asset``/``timeframe``/``side``/``status`` are NOT-NULL String
    identifiers — drift in length would silently truncate inserts.
  * Numeric precision pin: entry_price/stop_price/target_price/exit_price
    are Numeric(20, 8); pnl_amount is Numeric(20, 4); pnl_pct is
    Numeric(10, 6); r_multiple is Numeric(10, 4). Drift in any of these
    would silently corrupt the trade ledger.
  * ``status`` defaults to "open" (Python-side default) — guards against
    a NULL being treated as "closed" in metric rollups.
  * ``metadata_json`` JSONB nullable.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Mock trades are READ-ONLY for the trading path. The auto-trading
      gate ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.mock_trade import MockTrade


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "backtest_run_id": (False, None, None),
    "strategy_config_id": (True, None, None),
    "asset": (False, String, 50),
    "timeframe": (False, String, 10),
    "side": (False, String, 10),
    "entry_time": (False, DateTime, None),
    "entry_price": (False, Numeric, None),
    "stop_price": (True, Numeric, None),
    "target_price": (True, Numeric, None),
    "exit_time": (True, DateTime, None),
    "exit_price": (True, Numeric, None),
    "status": (False, String, 20),
    "result": (True, String, 20),
    "pnl_amount": (True, Numeric, None),
    "pnl_pct": (True, Numeric, None),
    "r_multiple": (True, Numeric, None),
    "reason_for_entry": (True, Text, None),
    "reason_for_exit": (True, Text, None),
    "metadata_json": (True, None, None),
}


PRICE_NUMERIC_20_8_COLUMNS: list[str] = [
    "entry_price", "stop_price", "target_price", "exit_price",
]


def test_table_name_unchanged():
    assert MockTrade.__tablename__ == "mock_trades"


def test_business_column_set_unchanged():
    table_cols = set(MockTrade.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"MockTrade missing column(s): {sorted(missing)}."
    assert not extra, f"MockTrade has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = MockTrade.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"MockTrade.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_pinned():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String:
            continue
        col = MockTrade.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"MockTrade.{col_name} String length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_soft_fk_uuids_no_formal_fk():
    for col_name in ("backtest_run_id", "strategy_config_id"):
        col = MockTrade.__table__.columns[col_name]
        assert isinstance(col.type, UUID)
        assert col.index is True, (
            f"MockTrade.{col_name}.index drifted: expected True."
        )
        assert len(list(col.foreign_keys)) == 0, (
            f"MockTrade.{col_name} unexpectedly has FK; soft-ref pattern."
        )


def test_price_numeric_precision_20_8_unchanged():
    for col_name in PRICE_NUMERIC_20_8_COLUMNS:
        col = MockTrade.__table__.columns[col_name]
        assert isinstance(col.type, Numeric), (
            f"MockTrade.{col_name} type drifted."
        )
        assert col.type.precision == 20, (
            f"MockTrade.{col_name}.precision drifted: expected 20, got {col.type.precision}."
        )
        assert col.type.scale == 8, (
            f"MockTrade.{col_name}.scale drifted: expected 8, got {col.type.scale}."
        )


def test_pnl_numeric_precisions_unchanged():
    pnl_amt = MockTrade.__table__.columns["pnl_amount"]
    assert isinstance(pnl_amt.type, Numeric)
    assert (pnl_amt.type.precision, pnl_amt.type.scale) == (20, 4), (
        f"MockTrade.pnl_amount precision/scale drifted: "
        f"got ({pnl_amt.type.precision}, {pnl_amt.type.scale})."
    )

    pnl_pct = MockTrade.__table__.columns["pnl_pct"]
    assert isinstance(pnl_pct.type, Numeric)
    assert (pnl_pct.type.precision, pnl_pct.type.scale) == (10, 6), (
        f"MockTrade.pnl_pct precision/scale drifted: "
        f"got ({pnl_pct.type.precision}, {pnl_pct.type.scale})."
    )

    r = MockTrade.__table__.columns["r_multiple"]
    assert isinstance(r.type, Numeric)
    assert (r.type.precision, r.type.scale) == (10, 4), (
        f"MockTrade.r_multiple precision/scale drifted: "
        f"got ({r.type.precision}, {r.type.scale})."
    )


def test_status_default_open_unchanged():
    col = MockTrade.__table__.columns["status"]
    assert col.default is not None
    default_value = col.default.arg
    if callable(default_value):
        default_value = default_value({})
    assert default_value == "open", (
        f"MockTrade.status default drifted: expected 'open', got {default_value!r}."
    )


def test_metadata_json_is_jsonb_family():
    col = MockTrade.__table__.columns["metadata_json"]
    assert type(col.type).__name__ in JSON_TYPE_NAMES, (
        f"MockTrade.metadata_json type drifted: got {type(col.type).__name__}."
    )


def test_entry_time_is_timezone_aware():
    col = MockTrade.__table__.columns["entry_time"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True, (
        "MockTrade.entry_time.timezone drifted: expected True."
    )
