"""Contract resolution service — lookup and cache IBKR contract IDs."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.broker.broker_interface import ContractLookupBroker
from app.db.models.asset import Asset

_logger = logging.getLogger(__name__)


class ContractResolutionService:
    """Resolve trading symbols to IBKR contract IDs (conid) and cache results."""

    def __init__(self, adapter: ContractLookupBroker, db: Session):
        self._adapter = adapter
        self._db = db

    async def resolve_symbol(
        self, symbol: str, sec_type: str = "STK", cache: bool = True
    ) -> int:
        """Resolve a symbol to contract ID.

        First checks database cache (if cache=True), then queries IBKR,
        then saves result to database.

        Args:
            symbol:   Trading symbol (e.g. "AAPL", "EURUSD")
            sec_type: Security type (STK, FUT, OPT, CASH, etc.)
            cache:    If True, use and update DB cache

        Returns:
            Contract ID (conid) as int

        Raises:
            ValueError: If symbol not found
        """
        # Check DB cache
        if cache:
            asset = self._db.query(Asset).filter(
                Asset.symbol == symbol
            ).first()
            if asset and asset.ibkr_con_id:
                _logger.debug(
                    "Contract ID cache hit: %s -> conid=%d",
                    symbol,
                    asset.ibkr_con_id,
                )
                return asset.ibkr_con_id

        # Query IBKR adapter
        conid = await self._adapter.resolve_conid(symbol, sec_type=sec_type)

        # Cache in database
        if cache:
            asset = self._db.query(Asset).filter(
                Asset.symbol == symbol
            ).first()
            if asset:
                asset.ibkr_con_id = conid
                self._db.commit()
                _logger.info("Cached conid %d for %s", conid, symbol)
            else:
                _logger.debug(
                    "Asset %s not in DB; conid %d not persisted",
                    symbol,
                    conid,
                )

        return conid

    async def resolve_fx_pair(
        self, base: str, quote: str = "USD"
    ) -> Optional[int]:
        """Resolve an FX pair (e.g. EUR.USD) to contract ID.

        Args:
            base:  Base currency (e.g. EUR)
            quote: Quote currency (default USD)

        Returns:
            Contract ID or None if not found
        """
        pair_symbol = f"{base}.{quote}"
        try:
            return await self.resolve_symbol(pair_symbol, sec_type="CASH")
        except ValueError:
            _logger.warning("FX pair %s not found", pair_symbol)
            return None
