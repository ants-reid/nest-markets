"""Options chain service — lookup option contracts and build strategies."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.clients.broker.broker_interface import OptionChainBroker

_logger = logging.getLogger(__name__)


@dataclass
class OptionLeg:
    """Single leg of an options strategy."""

    conid: int
    right: str  # "CALL" or "PUT"
    strike: Decimal
    expiration: str  # YYYYMMDD
    quantity: float
    side: str  # "BUY" or "SELL"
    limit_price: Optional[Decimal] = None


@dataclass
class OptionStrategy:
    """Multi-leg options strategy (spread, collar, etc.)."""

    name: str  # "CALL_SPREAD", "COLLAR", "STRANGLE", etc.
    legs: list[OptionLeg]
    description: str = ""


class OptionChainService:
    """Service for options chains, lookups, and strategy building."""

    def __init__(self, adapter: OptionChainBroker):
        self._adapter = adapter

    async def get_available_expirations(self, conid: int) -> list[str]:
        """Get available expiration dates for options on a contract.

        Args:
            conid: Underlying contract ID

        Returns:
            List of expirations in YYYYMMDD format
        """
        _logger.debug("Fetching option expirations for conid=%d", conid)

        expirations = await self._adapter.get_option_months(conid)

        _logger.info(
            "Found %d expirations for conid=%d",
            len(expirations),
            conid,
        )

        return expirations

    async def get_strikes(
        self, conid: int, expiration: str
    ) -> list[Decimal]:
        """Get available strikes for an expiration date.

        Args:
            conid:      Underlying contract ID
            expiration: Expiration date in YYYYMMDD format

        Returns:
            List of strikes as Decimals (sorted)
        """
        _logger.debug(
            "Fetching strikes for conid=%d, expiration=%s",
            conid,
            expiration,
        )

        strikes = await self._adapter.get_option_strikes(
            conid, expiration=expiration
        )

        strikes_decimal = [Decimal(str(s)) for s in strikes]
        strikes_decimal.sort()

        _logger.info(
            "Found %d strikes for conid=%d, expiration=%s",
            len(strikes_decimal),
            conid,
            expiration,
        )

        return strikes_decimal

    async def get_option_contracts(
        self,
        conid: int,
        expiration: str,
        right: str = "CALL",
    ) -> list[dict]:
        """Get all option contracts for a strike/expiration.

        Args:
            conid:      Underlying contract ID
            expiration: Expiration date in YYYYMMDD format
            right:      "CALL" or "PUT"

        Returns:
            List of contract dicts with conid, strike, right, expiration, etc.
        """
        _logger.debug(
            "Fetching %s contracts for conid=%d, expiration=%s",
            right,
            conid,
            expiration,
        )

        contracts = await self._adapter.get_option_contracts(
            conid, expiration=expiration, right=right
        )

        _logger.info(
            "Found %d %s contracts for conid=%d, expiration=%s",
            len(contracts),
            right,
            conid,
            expiration,
        )

        return contracts

    async def build_call_spread(
        self,
        conid: int,
        expiration: str,
        long_strike: Decimal,
        short_strike: Decimal,
        quantity: float = 100.0,
    ) -> OptionStrategy:
        """Build a call spread (debit or credit).

        Long call + short call at higher strike = debit spread (bullish)
        Short call + long call at higher strike = credit spread (bearish)

        Args:
            conid:        Underlying contract ID
            expiration:   Expiration in YYYYMMDD
            long_strike:  Lower strike (long)
            short_strike: Higher strike (short)
            quantity:     Contracts × 100 shares

        Returns:
            OptionStrategy with 2 legs
        """
        _logger.info(
            "Building call spread: %s %d shares, "
            "long %s call, short %s call, exp=%s",
            conid,
            quantity,
            long_strike,
            short_strike,
            expiration,
        )

        long_leg = OptionLeg(
            conid=conid,
            right="CALL",
            strike=long_strike,
            expiration=expiration,
            quantity=quantity,
            side="BUY",
        )

        short_leg = OptionLeg(
            conid=conid,
            right="CALL",
            strike=short_strike,
            expiration=expiration,
            quantity=quantity,
            side="SELL",
        )

        return OptionStrategy(
            name="CALL_SPREAD",
            legs=[long_leg, short_leg],
            description=f"Long {long_strike} / Short {short_strike} call spread",
        )

    async def build_put_spread(
        self,
        conid: int,
        expiration: str,
        long_strike: Decimal,
        short_strike: Decimal,
        quantity: float = 100.0,
    ) -> OptionStrategy:
        """Build a put spread.

        Long put + short put at lower strike = debit spread (bearish)
        Short put + long put at lower strike = credit spread (bullish)

        Args:
            conid:        Underlying contract ID
            expiration:   Expiration in YYYYMMDD
            long_strike:  Higher strike (long)
            short_strike: Lower strike (short)
            quantity:     Contracts × 100 shares

        Returns:
            OptionStrategy with 2 legs
        """
        _logger.info(
            "Building put spread: %s %d shares, "
            "long %s put, short %s put, exp=%s",
            conid,
            quantity,
            long_strike,
            short_strike,
            expiration,
        )

        long_leg = OptionLeg(
            conid=conid,
            right="PUT",
            strike=long_strike,
            expiration=expiration,
            quantity=quantity,
            side="BUY",
        )

        short_leg = OptionLeg(
            conid=conid,
            right="PUT",
            strike=short_strike,
            expiration=expiration,
            quantity=quantity,
            side="SELL",
        )

        return OptionStrategy(
            name="PUT_SPREAD",
            legs=[long_leg, short_leg],
            description=f"Long {long_strike} / Short {short_strike} put spread",
        )

    async def build_collar(
        self,
        conid: int,
        expiration: str,
        call_strike: Decimal,
        put_strike: Decimal,
        shares: float,
    ) -> OptionStrategy:
        """Build a protective collar (protective put + covered call).

        Typically used to protect long stock while selling upside.

        Args:
            conid:       Underlying contract ID
            expiration:  Expiration in YYYYMMDD
            call_strike: Short call strike (above current)
            put_strike:  Long put strike (below current)
            shares:      Number of underlying shares to protect

        Returns:
            OptionStrategy with 2 legs (put long, call short)
        """
        _logger.info(
            "Building collar: %s %d shares, "
            "long %s put, short %s call, exp=%s",
            conid,
            shares,
            put_strike,
            call_strike,
            expiration,
        )

        put_leg = OptionLeg(
            conid=conid,
            right="PUT",
            strike=put_strike,
            expiration=expiration,
            quantity=shares / 100.0,  # Convert to option contracts
            side="BUY",
        )

        call_leg = OptionLeg(
            conid=conid,
            right="CALL",
            strike=call_strike,
            expiration=expiration,
            quantity=shares / 100.0,
            side="SELL",
        )

        return OptionStrategy(
            name="COLLAR",
            legs=[put_leg, call_leg],
            description=f"Collar: long {put_strike} put / short {call_strike} call",
        )
