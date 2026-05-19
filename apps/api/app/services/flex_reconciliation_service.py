"""Flex Web Service reconciliation — daily activity statement comparison.

Uses the IBKR Flex Web Service two-step HTTP flow:
  1. POST https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest
     → returns reference code
  2. GET  https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement
     → returns XML activity statement

Token and query ID loaded exclusively from environment — never hardcoded.

Rate limit: 10 requests/min (enforced by retry logic).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from xml.etree import ElementTree

import httpx

from sqlalchemy.orm import Session

from app.db.models.position import Position
from app.db.models.asset import Asset

_logger = logging.getLogger(__name__)

# Flex Web Service base URL
_FLEX_BASE_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService"

# Rate limit: minimum seconds between requests
_MIN_REQUEST_INTERVAL_S = 6.1  # ~10 req/min


@dataclass
class FlexPosition:
    """Single position entry from a Flex activity statement."""

    account_id: str
    symbol: str
    conid: int
    quantity: Decimal
    cost_basis: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    currency: str = "USD"


@dataclass
class FlexReconciliationReport:
    """Result of comparing DB positions vs IBKR activity statement."""

    matched: int = 0
    missing_in_db: list[str] = field(default_factory=list)
    missing_in_ibkr: list[str] = field(default_factory=list)
    quantity_mismatches: dict[str, dict] = field(default_factory=dict)


class FlexReconciliationService:
    """Fetch and reconcile daily activity statement vs DB positions.

    Security: token and query ID loaded from environment variables only.
    """

    def __init__(self, db: Session, http_client: Optional[httpx.AsyncClient] = None):
        self._db = db
        self._http = http_client or httpx.AsyncClient(timeout=30.0)
        self._last_request_ts: float = 0.0

    def _get_credentials(self) -> tuple[str, str]:
        """Load Flex token and query ID from environment.

        Returns:
            (token, query_id) tuple

        Raises:
            ValueError: If credentials not set in environment
        """
        token = os.getenv("FLEX_TOKEN")
        query_id = os.getenv("FLEX_QUERY_ID")
        if not token or not query_id:
            raise ValueError(
                "FLEX_TOKEN and FLEX_QUERY_ID must be set as environment variables"
            )
        return token, query_id

    async def _rate_limited_request(self) -> None:
        """Enforce 10 req/min rate limit."""
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < _MIN_REQUEST_INTERVAL_S:
            import asyncio
            await asyncio.sleep(_MIN_REQUEST_INTERVAL_S - elapsed)
        self._last_request_ts = time.monotonic()

    async def fetch_activity_statement(self) -> list[FlexPosition]:
        """Fetch prior-day activity statement via two-step Flex Web Service.

        Step 1: SendRequest → reference code
        Step 2: GetStatement → XML payload

        Returns:
            List of FlexPosition records from the statement

        Raises:
            ValueError: If credentials not configured
            httpx.HTTPError: On HTTP failure
            ElementTree.ParseError: On malformed XML
        """
        token, query_id = self._get_credentials()

        # Step 1: request the statement
        await self._rate_limited_request()
        _logger.info("Requesting Flex activity statement (query_id=%s)", query_id)

        send_response = await self._http.get(
            f"{_FLEX_BASE_URL}.SendRequest",
            params={"t": token, "q": query_id, "v": "3"},
        )
        send_response.raise_for_status()

        # Parse reference code from response XML
        root = ElementTree.fromstring(send_response.text)
        ref_code = root.findtext("ReferenceCode")
        status = root.findtext("Status")

        if status != "Success" or not ref_code:
            raise ValueError(
                f"Flex SendRequest failed: status={status}, xml={send_response.text[:200]}"
            )

        _logger.info("Flex reference code: %s", ref_code)

        # Step 2: retrieve the statement
        await self._rate_limited_request()

        stmt_response = await self._http.get(
            f"{_FLEX_BASE_URL}.GetStatement",
            params={"t": token, "q": ref_code, "v": "3"},
        )
        stmt_response.raise_for_status()

        return self._parse_positions(stmt_response.text)

    def _parse_positions(self, xml_text: str) -> list[FlexPosition]:
        """Parse position records from Flex XML activity statement.

        Args:
            xml_text: Raw XML response from Flex Web Service

        Returns:
            List of FlexPosition records
        """
        positions: list[FlexPosition] = []

        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            _logger.error("Failed to parse Flex XML: %s", exc)
            raise

        # OpenPosition elements are in FlexQueryResponse/FlexStatements/FlexStatement/OpenPositions
        for pos_elem in root.iter("OpenPosition"):
            try:
                positions.append(
                    FlexPosition(
                        account_id=pos_elem.get("accountId", ""),
                        symbol=pos_elem.get("symbol", ""),
                        conid=int(pos_elem.get("conid", 0)),
                        quantity=Decimal(pos_elem.get("position", "0")),
                        cost_basis=Decimal(pos_elem.get("costBasisMoney", "0")),
                        market_value=Decimal(pos_elem.get("markPrice", "0")),
                        unrealized_pnl=Decimal(pos_elem.get("fifoPnlUnrealized", "0")),
                        realized_pnl=Decimal(pos_elem.get("realizedPnl", "0")),
                        currency=pos_elem.get("currency", "USD"),
                    )
                )
            except (ValueError, TypeError) as exc:
                _logger.warning("Skipping malformed position element: %s", exc)

        _logger.info("Parsed %d positions from Flex statement", len(positions))
        return positions

    async def reconcile(self) -> FlexReconciliationReport:
        """Compare DB positions vs IBKR Flex statement.

        Returns:
            FlexReconciliationReport with matched, missing, and mismatch counts
        """
        _logger.info("Starting Flex reconciliation")

        flex_positions = await self.fetch_activity_statement()
        flex_by_symbol = {p.symbol: p for p in flex_positions}

        db_rows = (
            self._db.query(Position, Asset.symbol)
            .join(Asset, Position.asset_id == Asset.id)
            .filter(Position.qty.isnot(None), Position.qty != 0)
            .all()
        )
        # Each row is (Position, symbol_str)
        db_by_symbol = {symbol: pos for pos, symbol in db_rows}

        report = FlexReconciliationReport()

        # Check positions in IBKR not in DB
        for symbol, flex_pos in flex_by_symbol.items():
            if symbol not in db_by_symbol:
                report.missing_in_db.append(symbol)
            else:
                db_pos = db_by_symbol[symbol]
                report.matched += 1

                # Check for quantity mismatches
                db_qty = Decimal(str(getattr(db_pos, "qty", 0) or 0))
                if abs(db_qty - flex_pos.quantity) > Decimal("0.001"):
                    report.quantity_mismatches[symbol] = {
                        "db_quantity": str(db_qty),
                        "ibkr_quantity": str(flex_pos.quantity),
                        "difference": str(abs(db_qty - flex_pos.quantity)),
                    }

        # Check positions in DB not in IBKR
        for symbol in db_by_symbol:
            if symbol not in flex_by_symbol:
                report.missing_in_ibkr.append(symbol)

        _logger.info(
            "Reconciliation complete: matched=%d, missing_in_db=%d, "
            "missing_in_ibkr=%d, quantity_mismatches=%d",
            report.matched,
            len(report.missing_in_db),
            len(report.missing_in_ibkr),
            len(report.quantity_mismatches),
        )

        return report
