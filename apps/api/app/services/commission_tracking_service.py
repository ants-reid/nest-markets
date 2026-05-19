"""Commission tracking service — fetch and persist trade commissions from IBKR.

After an order fills, call GET /iserver/account/trades to retrieve the
execution record; extract commission and net_amount; persist to the
PaperOrder row.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.broker.broker_interface import TradeHistoryBroker
from app.db.models.paper_order import PaperOrder

_logger = logging.getLogger(__name__)


@dataclass
class TradeExecution:
    """Single execution record from IBKR trade history."""

    order_id: str
    broker_order_id: str
    ticker: str
    side: str
    quantity: Decimal
    fill_price: Decimal
    commission: Decimal
    net_amount: Decimal
    execution_time: str


class CommissionTrackingService:
    """Fetch and persist commission data for filled orders.

    Uses GET /iserver/account/trades to retrieve current-day executions,
    matches by order_id, and updates PaperOrder.commission and
    PaperOrder.avg_fill_price.
    """

    def __init__(self, adapter: TradeHistoryBroker, db: Session):
        self._adapter = adapter
        self._db = db

    async def get_today_executions(self) -> list[TradeExecution]:
        """Fetch current-day trade executions from IBKR.

        Returns:
            List of TradeExecution records for today's filled orders
        """
        _logger.info("Fetching today's trade executions")

        raw_trades = await self._adapter.get_trades()

        executions = []
        for trade in raw_trades:
            try:
                executions.append(
                    TradeExecution(
                        order_id=str(trade.get("orderId", "")),
                        broker_order_id=str(trade.get("order_ref", "")),
                        ticker=trade.get("symbol", ""),
                        side=trade.get("side", ""),
                        quantity=Decimal(str(trade.get("size", 0))),
                        fill_price=Decimal(str(trade.get("price", 0))),
                        commission=Decimal(str(trade.get("commission", 0))),
                        net_amount=Decimal(str(trade.get("net_amount", 0))),
                        execution_time=str(trade.get("trade_time", "")),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                _logger.warning("Could not parse trade record: %s — %s", trade, exc)

        _logger.info("Fetched %d executions", len(executions))
        return executions

    async def update_order_commission(
        self, broker_order_id: str
    ) -> Optional[PaperOrder]:
        """Fetch commissions for a specific order and update the DB record.

        Args:
            broker_order_id: The broker's order ID

        Returns:
            Updated PaperOrder, or None if not found
        """
        executions = await self.get_today_executions()

        matching = [
            e for e in executions if e.broker_order_id == broker_order_id
        ]

        if not matching:
            _logger.info(
                "No execution found for broker_order_id=%s", broker_order_id
            )
            return None

        execution = matching[0]
        order = (
            self._db.query(PaperOrder)
            .filter(PaperOrder.broker_order_id == broker_order_id)
            .first()
        )

        if not order:
            _logger.warning(
                "PaperOrder not found for broker_order_id=%s", broker_order_id
            )
            return None

        order.commission = execution.commission
        order.avg_fill_price = execution.fill_price
        self._db.commit()

        _logger.info(
            "Updated commission for order %s: commission=%.4f, fill_price=%.4f",
            broker_order_id,
            execution.commission,
            execution.fill_price,
        )

        return order

    async def reconcile_all_commissions(self) -> dict:
        """Update commissions for all unfilled commission records in DB.

        Returns:
            Summary dict: {updated: int, not_found: int, already_set: int}
        """
        executions = await self.get_today_executions()
        execution_map = {e.broker_order_id: e for e in executions}

        # Find orders that are filled but have no commission yet
        pending_orders = (
            self._db.query(PaperOrder)
            .filter(
                PaperOrder.broker_order_id.isnot(None),
                PaperOrder.commission.is_(None),
            )
            .all()
        )

        updated = 0
        not_found = 0

        for order in pending_orders:
            exec_record = execution_map.get(order.broker_order_id)
            if exec_record:
                order.commission = exec_record.commission
                order.avg_fill_price = exec_record.fill_price
                updated += 1
            else:
                not_found += 1

        if updated:
            self._db.commit()
            _logger.info("Commission reconciliation: updated %d orders", updated)

        return {
            "updated": updated,
            "not_found": not_found,
            "total_pending": len(pending_orders),
        }
