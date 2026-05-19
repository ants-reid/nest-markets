"""MH-47 broker trade/fill normalization and staging service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.broker_trade_event import BrokerTradeEvent


@dataclass
class NormalizedTradeEvent:
    broker_order_id: str | None
    external_trade_id: str | None
    symbol: str | None
    side: str | None
    quantity: float | None
    fill_price: float | None
    commission: float | None
    net_amount: float | None
    realized_pnl: float | None
    trade_ts: datetime | None
    event_fingerprint: str
    raw_json: dict[str, Any]


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_trade_ts(raw: dict[str, Any]) -> datetime | None:
    for key in ("trade_time", "execution_time", "timestamp", "trade_ts"):
        val = raw.get(key)
        if not val:
            continue
        txt = str(val).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(txt)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def normalize_trade_event(raw: dict[str, Any]) -> NormalizedTradeEvent:
    """Normalize a raw broker trade/fill payload into stable internal shape."""
    broker_order_id = str(raw.get("order_ref") or raw.get("broker_order_id") or "").strip() or None
    external_trade_id = str(raw.get("orderId") or raw.get("execId") or raw.get("trade_id") or "").strip() or None
    symbol = str(raw.get("symbol") or raw.get("ticker") or "").strip().upper() or None
    side = str(raw.get("side") or "").strip().upper() or None

    quantity = _to_float(raw.get("size") if raw.get("size") is not None else raw.get("quantity"))
    fill_price = _to_float(raw.get("price") if raw.get("price") is not None else raw.get("fill_price"))
    commission = _to_float(raw.get("commission"))
    net_amount = _to_float(raw.get("net_amount"))
    realized_pnl = _to_float(raw.get("realizedPnl") or raw.get("realized_pnl") or raw.get("realized"))
    trade_ts = _parse_trade_ts(raw)

    fingerprint_seed = "|".join(
        [
            broker_order_id or "",
            external_trade_id or "",
            symbol or "",
            side or "",
            str(quantity) if quantity is not None else "",
            str(fill_price) if fill_price is not None else "",
            trade_ts.isoformat() if trade_ts is not None else "",
        ]
    )
    event_fingerprint = hashlib.sha256(fingerprint_seed.encode("utf-8")).hexdigest()

    return NormalizedTradeEvent(
        broker_order_id=broker_order_id,
        external_trade_id=external_trade_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        fill_price=fill_price,
        commission=commission,
        net_amount=net_amount,
        realized_pnl=realized_pnl,
        trade_ts=trade_ts,
        event_fingerprint=event_fingerprint,
        raw_json=raw,
    )


class BrokerTradeEventService:
    """Persist normalized broker trade events with stable provenance metadata."""

    def __init__(self, session: Session):
        self._session = session

    def ingest_trade_events(
        self,
        raw_events: list[dict[str, Any]],
        *,
        broker_provider: str,
        account_id: str | None,
        source: str,
    ) -> dict[str, int]:
        inserted = 0
        skipped = 0

        for raw in raw_events:
            if not isinstance(raw, dict):
                skipped += 1
                continue

            event = normalize_trade_event(raw)
            existing = (
                self._session.query(BrokerTradeEvent)
                .filter(BrokerTradeEvent.event_fingerprint == event.event_fingerprint)
                .first()
            )
            if existing is not None:
                skipped += 1
                continue

            row = BrokerTradeEvent(
                broker_provider=broker_provider,
                account_id=account_id,
                source=source,
                event_fingerprint=event.event_fingerprint,
                external_trade_id=event.external_trade_id,
                broker_order_id=event.broker_order_id,
                symbol=event.symbol,
                side=event.side,
                quantity=event.quantity,
                fill_price=event.fill_price,
                commission=event.commission,
                net_amount=event.net_amount,
                realized_pnl=event.realized_pnl,
                trade_ts=event.trade_ts,
                metadata_json={"normalization_version": "mh47-v1"},
                raw_json=event.raw_json,
            )
            self._session.add(row)
            inserted += 1

        return {
            "received": len(raw_events),
            "inserted": inserted,
            "skipped": skipped,
        }


def sum_today_realized_pnl_from_raw_events(raw_events: list[dict[str, Any]]) -> float | None:
    """Return today's summed realized P&L from normalized trade events."""
    today = date.today()
    vals: list[float] = []

    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        event = normalize_trade_event(raw)
        if event.realized_pnl is None:
            continue
        if event.trade_ts is not None and event.trade_ts.date() != today:
            continue
        vals.append(event.realized_pnl)

    return float(sum(vals)) if vals else None
