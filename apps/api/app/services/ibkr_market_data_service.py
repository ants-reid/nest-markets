"""IBKR market data service — real-time quotes and historical bars."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from app.clients.broker.broker_interface import MarketDataBroker

_logger = logging.getLogger(__name__)


class IBKRMarketDataService:
    """Service for IBKR market data: snapshots, quotes, historical bars."""

    def __init__(self, adapter: MarketDataBroker):
        self._adapter = adapter

    async def get_snapshot(
        self, conid: int, fields: str | None = None
    ) -> dict:
        """Get real-time market snapshot for a contract.

        Args:
            conid:  Contract ID
            fields: Comma-separated field list (e.g. 'bid,ask,last')
                    If None, returns full snapshot

        Returns:
            Market snapshot dict with bid, ask, last, volume, etc.
        """
        _logger.debug("Fetching snapshot for conid=%d", conid)

        snapshot = await self._adapter.get_snapshot(conid, fields=fields)

        _logger.debug(
            "Got snapshot: conid=%d, bid=%.2f, ask=%.2f",
            conid,
            snapshot.get("bid", 0),
            snapshot.get("ask", 0),
        )

        return snapshot

    async def get_bid_ask(self, conid: int) -> dict:
        """Get current bid/ask spread for a contract.

        Args:
            conid: Contract ID

        Returns:
            Dict with 'bid', 'ask', 'bid_size', 'ask_size'
        """
        snapshot = await self.get_snapshot(conid, fields="bid,ask,bidSize,askSize")
        return {
            "bid": snapshot.get("bid"),
            "ask": snapshot.get("ask"),
            "bid_size": snapshot.get("bidSize"),
            "ask_size": snapshot.get("askSize"),
        }

    async def get_last_price(self, conid: int) -> Optional[Decimal]:
        """Get last traded price.

        Args:
            conid: Contract ID

        Returns:
            Last traded price as Decimal, or None if not available
        """
        snapshot = await self.get_snapshot(conid, fields="last")
        last = snapshot.get("last")
        return Decimal(str(last)) if last is not None else None

    async def get_historical_data(
        self,
        conid: int,
        period: str,
        bar: str = "1d",
        outside_rth: bool = False,
    ) -> list[dict]:
        """Get historical OHLC bars.

        Args:
            conid:       Contract ID
            period:      Time period (e.g. "1mo", "1y", "5y")
            bar:         Bar size (1m, 5m, 1h, 1d, 1w, 1mo)
            outside_rth: Include outside regular trading hours

        Returns:
            List of bar dicts: [t, o, h, l, c, v]
        """
        _logger.info(
            "Fetching history: conid=%d, period=%s, bar=%s",
            conid,
            period,
            bar,
        )

        bars = await self._adapter.get_history(
            conid=conid,
            period=period,
            bar=bar,
            outside_rth=outside_rth,
        )

        _logger.info("Got %d bars for conid=%d", len(bars), conid)

        return bars

    async def unsubscribe_snapshot(self, conid: int) -> None:
        """Stop streaming snapshot for a contract.

        Args:
            conid: Contract ID
        """
        _logger.debug("Unsubscribing snapshot for conid=%d", conid)
        await self._adapter.unsubscribe_snapshot(conid)

    async def unsubscribe_all_snapshots(self) -> None:
        """Stop all active snapshot streams."""
        _logger.debug("Unsubscribing all snapshots")
        await self._adapter.unsubscribe_all_snapshots()
