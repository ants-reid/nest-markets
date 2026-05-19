"""IBKR P&L service — fetch partitioned P&L via REST API.

Uses GET /iserver/account/pnl/partitioned to retrieve daily P&L,
unrealized P&L, and net liquidation values.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.clients.broker.broker_interface import PnLBroker

_logger = logging.getLogger(__name__)


@dataclass
class IBKRPnLSummary:
    """P&L summary from IBKR partitioned endpoint."""

    account_id: str
    daily_pnl: Decimal
    unrealized_pnl: Decimal
    net_liquidation: Decimal


class IBKRPnLService:
    """Service for P&L retrieval via IBKR partitioned endpoint.

    Initial request may return empty upnl dict — service retries once
    per the API docs (first call is a subscription request).
    """

    MAX_RETRIES = 2

    def __init__(self, adapter: PnLBroker):
        self._adapter = adapter

    async def get_pnl(self, account_id: str) -> Optional[IBKRPnLSummary]:
        """Fetch P&L for the given account.

        Calls GET /iserver/account/pnl/partitioned and extracts values
        from the "{account_id}.Core" key in the upnl dict.

        Args:
            account_id: IBKR account ID (e.g. "DU12345")

        Returns:
            IBKRPnLSummary or None if unavailable after retries
        """
        _logger.info("Fetching P&L for account %s", account_id)

        for attempt in range(1, self.MAX_RETRIES + 1):
            raw = await self._adapter.get_pnl()
            upnl = raw.get("upnl", {})

            # IBKR keys the sub-account data as "{accountId}.Core"
            core_key = f"{account_id}.Core"
            core_data = upnl.get(core_key)

            if core_data:
                summary = IBKRPnLSummary(
                    account_id=account_id,
                    daily_pnl=Decimal(str(core_data.get("dpl", 0))),
                    unrealized_pnl=Decimal(str(core_data.get("upl", 0))),
                    net_liquidation=Decimal(str(core_data.get("nl", 0))),
                )
                _logger.info(
                    "P&L for %s: dpl=%.2f upl=%.2f nl=%.2f",
                    account_id,
                    summary.daily_pnl,
                    summary.unrealized_pnl,
                    summary.net_liquidation,
                )
                return summary

            _logger.debug(
                "P&L response empty on attempt %d/%d (initial subscription)",
                attempt,
                self.MAX_RETRIES,
            )

        _logger.warning(
            "P&L unavailable for account %s after %d attempts",
            account_id,
            self.MAX_RETRIES,
        )
        return None

    async def get_aggregate_pnl(self) -> dict[str, IBKRPnLSummary]:
        """Fetch P&L for all sub-accounts in the upnl response.

        Returns:
            Dict keyed by account_id → IBKRPnLSummary
        """
        _logger.info("Fetching aggregate P&L")

        raw = await self._adapter.get_pnl()
        upnl = raw.get("upnl", {})

        result: dict[str, IBKRPnLSummary] = {}
        for key, data in upnl.items():
            # Keys are like "DU12345.Core" — strip the ".Core" suffix
            account_id = key.replace(".Core", "")
            result[account_id] = IBKRPnLSummary(
                account_id=account_id,
                daily_pnl=Decimal(str(data.get("dpl", 0))),
                unrealized_pnl=Decimal(str(data.get("upl", 0))),
                net_liquidation=Decimal(str(data.get("nl", 0))),
            )

        _logger.info("Aggregate P&L: %d accounts", len(result))
        return result
