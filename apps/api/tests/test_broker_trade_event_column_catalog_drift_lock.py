"""Drift-lock: BrokerTradeEvent SQLA column catalog (cycle 73).

Pins the columns of the durable broker-side trade event record
(idempotent reconciliation rows). ``event_fingerprint`` is the
de-dup key — renaming it silently re-enables duplicate ingestion.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.broker_trade_event import BrokerTradeEvent

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "account_id",
        "broker_order_id",
        "broker_provider",
        "commission",
        "created_at",
        "event_fingerprint",
        "external_trade_id",
        "fill_price",
        "id",
        "metadata_json",
        "net_amount",
        "quantity",
        "raw_json",
        "realized_pnl",
        "side",
        "source",
        "symbol",
        "trade_ts",
    }
)
SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "broker_provider",
        "broker_order_id",
        "external_trade_id",
        "event_fingerprint",
        "symbol",
        "side",
        "quantity",
        "trade_ts",
    }
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in BrokerTradeEvent.__table__.columns)


def test_broker_trade_event_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "BrokerTradeEvent column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_broker_trade_event_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"BrokerTradeEvent missing safety/dedup column(s): "
        f"{sorted(missing)}."
    )
