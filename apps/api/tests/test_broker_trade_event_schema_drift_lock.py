"""Cycle 43 — Schema drift-lock for ``broker_trade_events``.

Locks the normalized broker trade/fill event surface — the broker
audit trail that future MH-15 reconciliation surfaces will consume.

Pinned shape:
  * 14 business columns + nullability + String lengths
  * UNIQUE constraint ``uq_broker_trade_event_fingerprint`` on
    ``event_fingerprint`` (idempotency / dedupe guarantee — a single
    broker fill cannot be ingested twice and silently double-count)
  * 5 indexed columns: account_id / event_fingerprint /
    broker_order_id / symbol / trade_ts
  * Numeric precision pin: quantity / fill_price / commission /
    net_amount / realized_pnl all (18, 8) — currency semantics
  * 2 JSONB-family columns: metadata_json, raw_json
  * Default identity values: broker_provider='ibkr',
    source='broker_account_trades' (matches the canonical ingest
    pipeline; drift here would silently change provenance)
  * event_fingerprint NOT NULL with no silent default — every audit
    row must explicitly carry its dedupe key.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Numeric, String

from app.db.models.broker_trade_event import BrokerTradeEvent


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "broker_provider": (False, String, 50),
    "account_id": (True, String, 64),
    "source": (False, String, 80),
    "event_fingerprint": (False, String, 128),
    "external_trade_id": (True, String, 128),
    "broker_order_id": (True, String, 128),
    "symbol": (True, String, 64),
    "side": (True, String, 16),
    "quantity": (True, Numeric, None),
    "fill_price": (True, Numeric, None),
    "commission": (True, Numeric, None),
    "net_amount": (True, Numeric, None),
    "realized_pnl": (True, Numeric, None),
    "trade_ts": (True, DateTime, None),
    "metadata_json": (True, None, None),  # JSONB
    "raw_json": (True, None, None),  # JSONB
}


PINNED_NUMERIC_18_8: list[str] = [
    "quantity",
    "fill_price",
    "commission",
    "net_amount",
    "realized_pnl",
]


JSONB_COLUMNS: list[str] = ["metadata_json", "raw_json"]


INDEXED_COLUMNS: list[str] = [
    "account_id",
    "event_fingerprint",
    "broker_order_id",
    "symbol",
    "trade_ts",
]


def test_table_name_unchanged():
    assert BrokerTradeEvent.__tablename__ == "broker_trade_events"


def test_business_column_set_unchanged():
    table_cols = set(BrokerTradeEvent.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"BrokerTradeEvent is missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"BrokerTradeEvent has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = BrokerTradeEvent.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"BrokerTradeEvent.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = BrokerTradeEvent.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"BrokerTradeEvent.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = BrokerTradeEvent.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"BrokerTradeEvent.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_columns_pinned_to_18_8():
    for col_name in PINNED_NUMERIC_18_8:
        col = BrokerTradeEvent.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 18, (
            f"BrokerTradeEvent.{col_name} precision drifted: "
            f"expected 18, got {col.type.precision}."
        )
        assert col.type.scale == 8, (
            f"BrokerTradeEvent.{col_name} scale drifted: "
            f"expected 8, got {col.type.scale}."
        )


def test_jsonb_columns_remain_jsonb_family():
    for col_name in JSONB_COLUMNS:
        col = BrokerTradeEvent.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES, (
            f"BrokerTradeEvent.{col_name} must remain a JSONB-family column; "
            f"got {type_name}."
        )


def test_event_fingerprint_unique_constraint_present():
    """Idempotency / dedupe guarantee — a single broker fill must not
    be ingested twice."""
    constraint_names = {
        c.name for c in BrokerTradeEvent.__table__.constraints if c.name
    }
    assert "uq_broker_trade_event_fingerprint" in constraint_names, (
        "UNIQUE constraint uq_broker_trade_event_fingerprint is missing — "
        "broker-fill dedupe guarantee is broken."
    )


def test_indexed_columns_remain_indexed():
    for col_name in INDEXED_COLUMNS:
        col = BrokerTradeEvent.__table__.columns[col_name]
        assert col.index is True, (
            f"BrokerTradeEvent.{col_name} must remain indexed (index=True)."
        )


def test_provenance_defaults_unchanged():
    """broker_provider='ibkr' / source='broker_account_trades' are the
    canonical pipeline values; drift here would silently change
    provenance attribution."""
    bp_col = BrokerTradeEvent.__table__.columns["broker_provider"]
    assert bp_col.default is not None
    assert bp_col.default.arg == "ibkr", (
        f"BrokerTradeEvent.broker_provider default drifted: "
        f"got {bp_col.default.arg!r}."
    )
    src_col = BrokerTradeEvent.__table__.columns["source"]
    assert src_col.default is not None
    assert src_col.default.arg == "broker_account_trades", (
        f"BrokerTradeEvent.source default drifted: got {src_col.default.arg!r}."
    )


def test_event_fingerprint_has_no_silent_default():
    """Every broker-fill audit row must explicitly carry its dedupe
    key — a default would let an empty insert collide on the unique
    index and either drop the event or alias it onto an unrelated one.
    """
    col = BrokerTradeEvent.__table__.columns["event_fingerprint"]
    assert col.default is None, (
        "BrokerTradeEvent.event_fingerprint gained a Python default."
    )
    assert col.server_default is None, (
        "BrokerTradeEvent.event_fingerprint gained a server_default."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = BrokerTradeEvent.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in BrokerTradeEvent.__table__.primary_key.columns]
    assert pk_cols == ["id"]
