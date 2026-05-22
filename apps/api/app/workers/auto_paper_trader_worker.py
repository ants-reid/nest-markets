"""AutoPaperTraderWorker — autonomously executes top-ranked signals as paper trades.

Workflow per run:
1. Load top-N ranked opportunities via OpportunityRankerService.
2. Check the auto-paper position cap (default MAX_OPEN_POSITIONS = 5).
3. For each opportunity (while cap not reached):
    a. Evaluate signal risk via RiskService.
    b. Route through BrokerService.submit_auto_order(...).
    c. Persist accepted, rejected, cancelled, or blocked outcomes accordingly.
4. Return a WorkerResult with counts.

Gate 10 compliance: risk gate (RiskService.evaluate) is ALWAYS called before any
PaperOrder row is created.  No position is opened with status other than "approved".
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clients.broker.broker_interface import OrderRequest, OrderResult
from app.config import get_settings
from app.db.enums import OrderStatus, PositionStatus, SignalStatus
from app.db.models.paper_order import PaperOrder
from app.db.models.position import Position
from app.db.models.risk_profile import RiskProfile
from app.db.models.signal import Signal
from app.db.session import SessionLocal
from app.services.broker_service import BrokerService, PaperPreflightBlockedError
from app.services.opportunity_ranker_service import OpportunityRankerService
from app.services.risk_service import RiskInput, RiskService
from app.services.trading_control_service import AutoTradingBlockedError
from app.workers.async_bridge import run_async
from app.workers.base_worker import BaseWorker

_logger = logging.getLogger(__name__)

# Maximum concurrent auto-paper positions (Gate 10 cap)
_DEFAULT_MAX_OPEN = 5

# Recency window passed to the ranker
_RECENCY_HOURS = 8
_ACCEPTED_BROKER_STATUSES = {"SUBMITTED", "FILLED"}
_REJECTED_BROKER_STATUSES = {"REJECTED", "CANCELLED"}


class AutoPaperTraderWorker(BaseWorker):
    """Select top-ranked opportunities and execute them as paper trades."""

    worker_name = "auto_paper_trader"

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def _get_broker_service(self) -> BrokerService:
        return BrokerService()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _count_open_auto_paper_positions(self, session: Session) -> int:
        """Return the number of currently open auto-paper positions."""
        count = session.execute(
            select(func.count()).where(
                Position.status == PositionStatus.OPEN,
                Position.close_reason == "auto_paper",
            )
        ).scalar_one()
        return int(count)

    def _load_risk_profile(self, session: Session) -> RiskProfile | None:
        """Load the first active risk profile."""
        return (
            session.query(RiskProfile)
            .filter(RiskProfile.is_active == "active")
            .first()
        )

    def _build_risk_input(self, opportunity, signal: Signal, risk_profile: RiskProfile) -> RiskInput:
        """Build a RiskInput from a ranked opportunity and its DB signal row."""
        return RiskInput(
            signal_id=opportunity.signal_id,
            asset_id=signal.asset_id,
            asset_symbol=opportunity.asset,
            direction=opportunity.direction,
            confidence=float(signal.confidence or 0.0),
            signal_score=float(signal.signal_score or 0.0),
            spread_bps=0.0,          # no live spread available for paper mode
            asset_type=opportunity.asset_class.value,
            daily_drawdown_pct=0.0,  # no live drawdown tracking yet
            open_positions_count=0,  # checked separately via cap
            recent_losses_count=0,   # no learning history yet
            last_loss_at=None,
            kill_switch_active=False,
            risk_profile=risk_profile,
        )

    def _build_broker_order_request(self, opportunity, signal: Signal) -> OrderRequest:
        """Build the broker-facing order request for the shared auto submit gate."""
        entry_price = signal.entry_min
        if entry_price is not None:
            return OrderRequest(
                ticker=opportunity.asset,
                side="BUY" if opportunity.direction == "long" else "SELL",
                quantity=Decimal("1.0"),
                order_type="LIMIT",
                limit_price=Decimal(str(entry_price)),
            )

        return OrderRequest(
            ticker=opportunity.asset,
            side="BUY" if opportunity.direction == "long" else "SELL",
            quantity=Decimal("1.0"),
            order_type="MARKET",
        )

    def _submit_via_broker_gate(self, opportunity, signal: Signal) -> OrderResult:
        """Route worker-driven auto paper submission through the broker auto-submit seam."""
        order_request = self._build_broker_order_request(opportunity, signal)
        return run_async(
            lambda: self._get_broker_service().submit_auto_order(order_request)
        )

    def _normalize_paper_order_status(self, broker_status: str) -> str:
        normalized = broker_status.upper()
        if normalized == "SUBMITTED":
            return OrderStatus.ACCEPTED.value
        if normalized == "FILLED":
            return OrderStatus.FILLED.value
        if normalized == "REJECTED":
            return OrderStatus.REJECTED.value
        if normalized == "CANCELLED":
            return OrderStatus.CANCELED.value
        return normalized.lower()

    def _coerce_numeric_broker_order_id(self, broker_order_id: str | None) -> int | None:
        if broker_order_id is None:
            return None
        try:
            return int(str(broker_order_id))
        except (TypeError, ValueError):
            return None

    def _record_broker_outcome(
        self,
        session: Session,
        opportunity,
        signal: Signal,
        broker_result: OrderResult,
    ) -> PaperOrder:
        """Persist the broker-facing paper order outcome regardless of acceptance."""
        entry_price = Decimal(str(signal.entry_min or broker_result.filled_price or 0.0))
        paper_order = PaperOrder(
            signal_id=opportunity.signal_id,
            asset_id=signal.asset_id,
            order_type="auto_paper",
            side=opportunity.direction,
            qty=Decimal("1.0"),
            quantity=Decimal("1.0"),
            filled_quantity=broker_result.filled_quantity,
            notional=entry_price,
            limit_price=Decimal(str(signal.entry_min)) if signal.entry_min is not None else None,
            stop_price=signal.stop_price,
            status=self._normalize_paper_order_status(broker_result.status),
            submitted_at=broker_result.submitted_at or datetime.now(UTC),
            timestamp=datetime.now(UTC),
            broker_order_id=self._coerce_numeric_broker_order_id(broker_result.broker_order_id),
            avg_fill_price=broker_result.filled_price,
            ibkr_status=broker_result.status,
        )
        session.add(paper_order)
        return paper_order

    def _open_position(
        self,
        session: Session,
        opportunity,
        signal: Signal,
        broker_result: OrderResult,
    ) -> None:
        """Persist accepted broker outcome and open a matching local position."""
        self._record_broker_outcome(session, opportunity, signal, broker_result)

        entry_price = Decimal(str(broker_result.filled_price or signal.entry_min or 0.0))

        position = Position(
            asset_id=signal.asset_id,
            signal_id=opportunity.signal_id,
            status=PositionStatus.OPEN,
            side=opportunity.direction,
            avg_entry_price=entry_price,
            current_price=entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            qty=Decimal("1.0"),
            opened_at=datetime.now(UTC),
            close_reason="auto_paper",  # tag for cap counting
            broker_order_id=broker_result.broker_order_id,
        )
        session.add(position)

        # Update signal status to paper_submitted
        signal.signal_status = SignalStatus.PAPER_SUBMITTED

    # ------------------------------------------------------------------
    # BaseWorker contract
    # ------------------------------------------------------------------

    def execute(self) -> str:
        settings = get_settings()
        max_open = getattr(settings, "auto_paper_max_open_positions", _DEFAULT_MAX_OPEN)

        session = self._session or SessionLocal()
        close_session = self._session is None

        opened = 0
        risk_blocked = 0
        gate_blocked = 0
        rejected = 0
        cancelled = 0
        unsupported = 0
        skipped_cap = 0

        try:
            ranker = OpportunityRankerService(session)
            opportunities = ranker.rank(limit=max_open, recency_hours=_RECENCY_HOURS)

            if not opportunities:
                return "auto_paper_trader: no ranked opportunities — skipped"

            risk_profile = self._load_risk_profile(session)
            if risk_profile is None:
                return "auto_paper_trader: no active risk profile — skipped"

            # Hard kill-switch check — abort entire batch immediately
            if risk_profile.kill_switch_enabled:
                return "auto_paper_trader: kill-switch active — all trading halted"

            risk_service = RiskService(session)

            for opportunity in opportunities:
                open_count = self._count_open_auto_paper_positions(session)
                if open_count >= max_open:
                    skipped_cap += 1
                    _logger.info(
                        "auto_paper_trader: position cap reached (%d/%d), skipping %s",
                        open_count,
                        max_open,
                        opportunity.asset,
                    )
                    continue

                signal = session.get(Signal, opportunity.signal_id)
                if signal is None:
                    _logger.warning("auto_paper_trader: signal %s not found", opportunity.signal_id)
                    continue

                risk_input = self._build_risk_input(opportunity, signal, risk_profile)
                risk_output = risk_service.evaluate(risk_input)  # Gate 10 — always called

                if not risk_output.approved:
                    risk_blocked += 1
                    _logger.info(
                        "auto_paper_trader: risk blocked %s — %s",
                        opportunity.asset,
                        risk_output.blocking_rule,
                    )
                    continue

                try:
                    broker_result = self._submit_via_broker_gate(opportunity, signal)
                except (AutoTradingBlockedError, PaperPreflightBlockedError) as exc:
                    gate_blocked += 1
                    _logger.info(
                        "auto_paper_trader: broker gate blocked %s — %s",
                        opportunity.asset,
                        exc,
                    )
                    continue

                normalized_status = broker_result.status.upper()

                if normalized_status in _REJECTED_BROKER_STATUSES:
                    self._record_broker_outcome(session, opportunity, signal, broker_result)
                    if normalized_status == "REJECTED":
                        rejected += 1
                    else:
                        cancelled += 1
                    _logger.info(
                        "auto_paper_trader: broker rejected %s — %s",
                        opportunity.asset,
                        broker_result.status,
                    )
                    continue

                if normalized_status not in _ACCEPTED_BROKER_STATUSES:
                    unsupported += 1
                    _logger.warning(
                        "auto_paper_trader: unsupported broker outcome %s for %s",
                        broker_result.status,
                        opportunity.asset,
                    )
                    continue

                self._open_position(session, opportunity, signal, broker_result)
                opened += 1
                _logger.info("auto_paper_trader: opened position for %s", opportunity.asset)

            session.commit()
        except Exception as exc:
            session.rollback()
            _logger.error("auto_paper_trader fatal error: %s", exc)
            return f"auto_paper_trader: fatal error — {exc}"
        finally:
            if close_session:
                session.close()

        parts = [f"auto_paper_trader: {opened} positions opened"]
        if risk_blocked:
            parts.append(f"{risk_blocked} risk-blocked")
        if gate_blocked:
            parts.append(f"{gate_blocked} gate-blocked")
        if rejected:
            parts.append(f"{rejected} rejected")
        if cancelled:
            parts.append(f"{cancelled} cancelled")
        if unsupported:
            parts.append(f"{unsupported} unsupported")
        if skipped_cap:
            parts.append(f"{skipped_cap} skipped (cap)")
        return ", ".join(parts)
