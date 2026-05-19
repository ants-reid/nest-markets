"""Live execution scaffold for MVP with explicit disabled behavior.

Execution mode semantics:
  auto_live  — always disabled (Gate 4 guard; never routes to broker)
    auto_paper — routes through the broker client layer to paper account when PAPER_TRADING_ENABLED=true
               and a broker is wired; otherwise returns disabled sentinel
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.clients.broker.broker_interface import BrokerInterface, OrderRequest, OrderResult
from app.db.models import AuditLog
from app.services.broker_service import BrokerService, PaperPreflightBlockedError
from app.services.trading_control_service import AutoTradingBlockedError

_logger = logging.getLogger(__name__)


class LiveExecutionDisabledError(Exception):
    """Raised when live execution is attempted while disabled in MVP."""


@dataclass(frozen=True)
class LiveExecutionRequest:
    """Future live execution request contract."""

    asset: str
    side: Literal["buy", "sell"]
    qty: float
    notional: float
    stop_price: float
    target_price: float
    execution_mode: str = "auto_paper"  # "auto_paper" | "auto_live"


@dataclass(frozen=True)
class LiveExecutionResult:
    """Live execution scaffold result for MVP."""

    accepted: bool
    status: Literal["disabled", "submitted", "paper_submitted"]
    reason: str
    processed_at: datetime
    broker_order_id: str | None = None


class LiveExecutionService:
    """Broker execution service.

    - auto_live mode: always disabled (Gate 4 invariant).
    - auto_paper mode: routes through broker adapter when PAPER_TRADING_ENABLED=true
      and a broker is wired; returns disabled sentinel otherwise.
    """

    def __init__(
        self,
        session: Session | None = None,
        broker: BrokerInterface | None = None,
    ) -> None:
        self._session = session
        self._broker = broker

    def _get_broker_service(self) -> BrokerService:
        return BrokerService(broker=self._broker)

    def is_live_enabled(self) -> bool:
        """Live (real money) execution — always False in MVP (Gate 4)."""
        return False

    def is_paper_enabled(self) -> bool:
        """Paper execution — enabled when env guard and broker are both present."""
        return bool(os.getenv("PAPER_TRADING_ENABLED")) and self._broker is not None

    # ── legacy property kept for backward compat ──────────────────────────────
    def is_enabled(self) -> bool:
        """Legacy: returns False; use is_paper_enabled() / is_live_enabled()."""
        return False

    def submit_order(
        self,
        risk_decision_id: UUID,
        asset_id: UUID,
        direction: str,
        quantity: float,
    ) -> None:
        """Always raise LiveExecutionDisabledError and log the attempt."""
        if self._session:
            audit = AuditLog(
                entity_type="live_execution",
                entity_id=risk_decision_id,
                event_type="submit_order_blocked",
                payload_json={"direction": direction, "quantity": quantity, "asset_id": str(asset_id)},
            )
            self._session.add(audit)
        raise LiveExecutionDisabledError("live_execution_disabled in MVP")

    def cancel_order(self, broker_order_id: str) -> None:
        """Always raise LiveExecutionDisabledError."""
        raise LiveExecutionDisabledError("live_execution_disabled in MVP")

    def submit(self, request: LiveExecutionRequest) -> LiveExecutionResult:
        """Route execution based on mode.

        - auto_live  → always returns disabled sentinel (Gate 4)
        - auto_paper → routes to broker adapter when PAPER_TRADING_ENABLED + broker wired
        """
        now = datetime.now(UTC)

        # Gate 4: live execution always disabled
        if request.execution_mode == "auto_live":
            _logger.info(
                "Live execution blocked (Gate 4): asset=%s side=%s qty=%s",
                request.asset,
                request.side,
                request.qty,
            )
            return LiveExecutionResult(
                accepted=False,
                status="disabled",
                reason="live_execution_disabled_in_mvp",
                processed_at=now,
            )

        # Paper path
        if not self.is_paper_enabled():
            return LiveExecutionResult(
                accepted=False,
                status="disabled",
                reason="live_execution_disabled_in_mvp",
                processed_at=now,
            )

        # Route through broker service seam (paper account)
        try:
            order_request = OrderRequest(
                ticker=request.asset,
                side=request.side.upper(),
                quantity=Decimal(str(request.qty)),
                order_type="MARKET",
            )
            result: OrderResult = asyncio.run(
                self._get_broker_service().submit_auto_order(order_request)
            )
            _logger.info(
                "Paper order submitted: asset=%s side=%s qty=%s broker_order_id=%s",
                request.asset,
                request.side,
                request.qty,
                result.broker_order_id,
            )
            return LiveExecutionResult(
                accepted=True,
                status="paper_submitted",
                reason="paper_order_submitted",
                processed_at=now,
                broker_order_id=result.broker_order_id,
            )
        except (AutoTradingBlockedError, PaperPreflightBlockedError) as exc:
            _logger.info("Auto paper execution blocked: %s", exc)
            return LiveExecutionResult(
                accepted=False,
                status="disabled",
                reason=str(exc),
                processed_at=now,
            )
        except Exception as exc:
            _logger.error("Paper order failed: %s", exc)
            return LiveExecutionResult(
                accepted=False,
                status="disabled",
                reason=f"paper_order_failed: {exc}",
                processed_at=now,
            )
