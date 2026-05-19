"""Advanced order service — bracket orders, OCA orders, algorithmic orders."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.clients.broker.broker_interface import AdvancedOrderBroker, OrderRequest, OrderResult
from app.services.trading_control_service import assert_order_submission_allowed

_logger = logging.getLogger(__name__)


@dataclass
class BracketOrderConfig:
    """Configuration for a bracket order (entry + take-profit + stop-loss)."""

    conid: int
    side: Literal["BUY", "SELL"]
    quantity: float
    entry_price: float
    take_profit_price: float
    stop_loss_price: float
    tif: str = "DAY"  # time-in-force


@dataclass
class AlgoOrderConfig:
    """Configuration for an algorithmic order (Adaptive, VWAP, TWAP)."""

    conid: int
    side: Literal["BUY", "SELL"]
    quantity: float
    algo_type: Literal["Adaptive", "Vwap", "Twap"]
    price: float
    max_pct_vol: float | None = None  # For VWAP
    tif: str = "DAY"
    outside_rth: bool = False


class AdvancedOrderService:
    """Service for complex order types (bracket, OCA, algorithmic)."""

    def __init__(self, adapter: AdvancedOrderBroker):
        self._adapter = adapter

    async def submit_bracket_order(
        self, config: BracketOrderConfig
    ) -> list[OrderResult]:
        """Submit a bracket order (entry + TP + SL) as a linked group.

        Args:
            config: BracketOrderConfig with entry, TP, SL details

        Returns:
            List of 3 OrderResults (entry, TP, SL)
        """
        assert_order_submission_allowed(intent="manual")

        _logger.info(
            "Submitting bracket order: %s %d %s @ %.2f "
            "(TP: %.2f, SL: %.2f)",
            config.side,
            config.quantity,
            config.conid,
            config.entry_price,
            config.take_profit_price,
            config.stop_loss_price,
        )

        results = await self._adapter.submit_bracket_order(
            conid=config.conid,
            side=config.side,
            quantity=config.quantity,
            entry_price=config.entry_price,
            take_profit_price=config.take_profit_price,
            stop_loss_price=config.stop_loss_price,
            tif=config.tif,
        )

        _logger.info(
            "Bracket order submitted: %d orders, status=%s",
            len(results),
            results[0].status if results else "unknown",
        )

        return results

    async def submit_oca_order(
        self, legs: list[dict]
    ) -> list[OrderResult]:
        """Submit a One-Cancels-All (OCA) order group.

        When one leg fills or is cancelled, all other legs are cancelled.

        Args:
            legs: List of order dicts (each must have conid, orderType, side, quantity, etc.)

        Returns:
            List of OrderResults for each leg
        """
        assert_order_submission_allowed(intent="manual")

        _logger.info("Submitting OCA order with %d legs", len(legs))

        results = await self._adapter.submit_oca_order(legs)

        _logger.info(
            "OCA order submitted: %d legs, status=%s",
            len(results),
            results[0].status if results else "unknown",
        )

        return results

    async def submit_algo_order(
        self, config: AlgoOrderConfig
    ) -> OrderResult:
        """Submit an algorithmic order (Adaptive, VWAP, TWAP).

        Args:
            config: AlgoOrderConfig with algo type and parameters

        Returns:
            OrderResult for the submitted algo order
        """
        assert_order_submission_allowed(intent="manual")

        _logger.info(
            "Submitting %s algo order: %s %d %s @ %.2f",
            config.algo_type,
            config.side,
            config.quantity,
            config.conid,
            config.price,
        )

        # Build order body based on algo type
        order_body = {
            "conid": config.conid,
            "secType": f"{config.conid}:STK",
            "orderType": "LMT",
            "side": config.side,
            "quantity": config.quantity,
            "price": config.price,
            "tif": config.tif,
            "outsideRTH": config.outside_rth,
        }

        # Add algo-specific parameters
        if config.algo_type == "Adaptive":
            order_body["useAdaptive"] = True
        elif config.algo_type in ("Vwap", "Twap"):
            order_body["algoStrategy"] = config.algo_type
            if config.max_pct_vol is not None:
                order_body["algoParams"] = [
                    {"tag": "maxPctVol", "value": config.max_pct_vol}
                ]

        # Submit via adapter
        result = await self._adapter.submit_order(
            OrderRequest(
                ticker=str(config.conid),
                side=config.side,
                quantity=Decimal(str(config.quantity)),
                order_type="LIMIT",
                limit_price=Decimal(str(config.price)),
                tif=config.tif,
                outside_rth=config.outside_rth,
            )
        )

        _logger.info(
            "%s algo order submitted: %s (status=%s)",
            config.algo_type,
            result.broker_order_id,
            result.status,
        )

        return result
