"""BrokerService — orchestrates order execution, account management, and positions."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.clients.broker.broker_interface import (
    AccountInfo,
    BrokerInterface,
    OrderRequest,
    OrderResult,
    PositionInfo,
)
from app.clients.broker.gateway_factory import BrokerGatewayFactory
from app.config import get_settings
from app.db.models.broker_trade_event import BrokerTradeEvent
from app.db.session import SessionLocal
from app.services.broker_preflight_advisory_service import BrokerPreflightAdvisoryService
from app.services.broker_preflight_decision_service import BrokerPreflightDecisionService
from app.services.broker_trade_event_service import (
    BrokerTradeEventService,
    sum_today_realized_pnl_from_raw_events,
)
from app.services.broker_mode_guard import (
    LiveExecutionBlockedError,
    get_broker_mode_metadata,
)
from app.services.trading_control_service import (
    AutoTradingBlockedError,
    LiveTradingNotArmedError,
    TradingControlError,
    TradingControlMisconfiguredError,
    assert_order_submission_allowed,
)

_logger = logging.getLogger(__name__)


class PaperPreflightBlockedError(TradingControlError):
    """Raised when paper submit is rejected by MH-78 preflight enforcement."""

    def __init__(
        self,
        *,
        preflight_decision: dict[str, Any],
        preflight_context: dict[str, Any],
    ) -> None:
        self.preflight_decision = preflight_decision
        self.preflight_context = preflight_context
        self.blocking_reasons = [
            *preflight_decision.get("blocking_items", []),
            *preflight_decision.get("would_block_items", []),
        ]

        reason_summary = "; ".join(
            item["message"] for item in self.blocking_reasons if item.get("message")
        )
        if not reason_summary:
            reason_summary = "One or more paper preflight checks failed."

        super().__init__(f"Paper order submission blocked by preflight checks: {reason_summary}")

    def to_response_detail(self) -> dict[str, Any]:
        return {
            "code": "paper_preflight_blocked",
            "message": "Paper order submission blocked by preflight checks.",
            "decision_status": self.preflight_decision.get("decision_status"),
            "submit_gate": self.preflight_decision.get("submit_gate"),
            "blocking_reasons": self.blocking_reasons,
            "preflight_decision": self.preflight_decision,
            "preflight_context": self.preflight_context,
        }


class BrokerService:
    """Orchestration service for broker operations.

    This service wraps a concrete BrokerInterface adapter and provides
    higher-level operations like order submission with validation and
    account reconciliation.
    """

    def __init__(self, broker: BrokerInterface | None = None) -> None:
        """Initialize with a broker adapter.

        If broker is None, a default IBKR adapter will be created on first use.
        """
        self._broker = broker
        self._cached_account_info: AccountInfo | None = None
        self._preflight_advisory = BrokerPreflightAdvisoryService()
        self._preflight_decisions = BrokerPreflightDecisionService()

    async def ensure_connected(self) -> None:
        """Ensure the broker adapter is initialized and connected."""
        if self._broker is None:
            settings = get_settings()
            factory = BrokerGatewayFactory()
            provider = (settings.broker_provider or "ibkr").lower()
            if provider in ("tws", "tws_socket"):
                if not settings.tws_enabled:
                    raise RuntimeError(
                        "BROKER_PROVIDER=tws requires TWS_ENABLED=true"
                    )
                meta = get_broker_mode_metadata()
                submit_ok = (
                    str(meta.get("mode") or "").lower() == "paper"
                    and bool(meta.get("paper_trading_enabled"))
                    and not bool(meta.get("live_execution_enabled"))
                )
                self._broker = factory.create(
                    "tws",
                    tws_host=settings.tws_host,
                    tws_port=settings.tws_port,
                    tws_client_id=settings.tws_client_id,
                    tws_submit_enabled=submit_ok,
                    preferred_account_id=settings.ibkr_account_id or None,
                )
            else:
                self._broker = factory.create(
                    "ibkr",
                    base_url=settings.ibkr_gateway_url,
                    preferred_account_id=settings.ibkr_account_id or None,
                )
        if hasattr(self._broker, "connect") and not getattr(self._broker, "is_connected", False):
            await self._broker.connect()

    async def get_account_info(self, use_cache: bool = False) -> AccountInfo:
        """Get account information.

        Args:
            use_cache: If True, return cached info (if available).
                      If False, always fetch fresh from broker.

        Returns:
            AccountInfo with balance and margin details.
        """
        await self.ensure_connected()
        assert self._broker is not None
        if use_cache and self._cached_account_info:
            return self._cached_account_info
        info = await self._broker.get_account_info()
        self._cached_account_info = info
        return info

    async def get_positions(self) -> list[PositionInfo]:
        """Get all open positions."""
        await self.ensure_connected()
        assert self._broker is not None
        return await self._broker.get_positions()

    async def _derive_closed_pnl_from_fill_events(self) -> tuple[float | None, str | None]:
        """Best-effort closed_pnl derivation from today's broker trade/fill events.

        Uses broker adapter trade history when available and sums realized fields
        (`realizedPnl`, `realized_pnl`, or `realized`). Returns (None, None)
        when no realized values are available.
        """
        await self.ensure_connected()
        assert self._broker is not None

        if not hasattr(self._broker, "get_trades"):
            return None, None

        get_trades = getattr(self._broker, "get_trades")
        if not callable(get_trades):
            return None, None

        try:
            raw_trades = await get_trades()
        except Exception:  # noqa: BLE001
            _logger.debug("Could not fetch trade events for closed_pnl derivation", exc_info=True)
            return None, None

        if not isinstance(raw_trades, list):
            return None, None

        closed_pnl = sum_today_realized_pnl_from_raw_events(raw_trades)
        if closed_pnl is None:
            return None, None

        return closed_pnl, "broker_trade_events"

    async def normalize_and_stage_trade_events(self, source: str = "broker_account_trades") -> dict[str, Any]:
        """Normalize and stage broker trade/fill events with stable provenance (MH-47).

        Backend ingestion/reconciliation only: this never submits orders and never
        mutates trading mode. Active account context is sourced from current settings.
        """
        settings = get_settings()
        account_id = settings.ibkr_account_id or None
        broker_mode = get_broker_mode_metadata()

        await self.ensure_connected()
        assert self._broker is not None

        if not hasattr(self._broker, "get_trades"):
            return {
                "received": 0,
                "inserted": 0,
                "skipped": 0,
                "source": source,
                "account_id": account_id,
                "broker_mode": broker_mode,
                "note": "Broker adapter has no trade-event API.",
            }

        raw_trades = await self._broker.get_trades()
        if not isinstance(raw_trades, list):
            raw_trades = []

        with SessionLocal() as session:
            svc = BrokerTradeEventService(session)
            summary = svc.ingest_trade_events(
                raw_trades,
                broker_provider=str(broker_mode.get("broker", "ibkr")),
                account_id=account_id,
                source=source,
            )
            session.commit()

        return {
            **summary,
            "source": source,
            "account_id": account_id,
            "broker_mode": broker_mode,
            "note": None,
        }

    def get_normalized_trade_events(self, limit: int = 100) -> dict[str, Any]:
        """Return recent normalized trade/fill events for provenance audit readback (MH-47B)."""
        settings = get_settings()
        account_id = settings.ibkr_account_id or None
        broker_mode = get_broker_mode_metadata()

        safe_limit = max(1, min(int(limit), 500))

        with SessionLocal() as session:
            rows = (
                session.query(BrokerTradeEvent)
                .order_by(BrokerTradeEvent.trade_ts.desc().nullslast(), BrokerTradeEvent.created_at.desc())
                .limit(safe_limit)
                .all()
            )

        entries: list[dict[str, Any]] = []
        for row in rows:
            entries.append(
                {
                    "event_fingerprint": row.event_fingerprint,
                    "external_trade_id": row.external_trade_id,
                    "broker_order_id": row.broker_order_id,
                    "symbol": row.symbol,
                    "side": row.side,
                    "quantity": float(row.quantity) if row.quantity is not None else None,
                    "fill_price": float(row.fill_price) if row.fill_price is not None else None,
                    "commission": float(row.commission) if row.commission is not None else None,
                    "net_amount": float(row.net_amount) if row.net_amount is not None else None,
                    "realized_pnl": float(row.realized_pnl) if row.realized_pnl is not None else None,
                    "trade_ts": row.trade_ts.isoformat() if row.trade_ts is not None else None,
                    "source": row.source,
                    "account_id": row.account_id,
                    "broker_provider": row.broker_provider,
                    "created_at": row.created_at.isoformat(),
                }
            )

        return {
            "entries": entries,
            "returned": len(entries),
            "account_id": account_id,
            "broker_mode": broker_mode,
        }

    async def capture_daily_pnl_snapshot(self, source: str = "manual") -> dict[str, Any]:
        """Capture and persist one P&L snapshot row (MH-46A).

        Data source:
        - Account balances via broker `get_account_info()`
        - Position list via broker `get_positions()`

        Safety guarantees:
        - Writes only to `pnl_snapshots`
        - Does not call any order submit/cancel path
        - Does not alter trading-mode guards or submit behavior
        """
        from app.services.pnl_service import PnlService, PnlSnapshotInput

        settings = get_settings()
        account_id = settings.ibkr_account_id or None
        broker_mode = get_broker_mode_metadata()

        account = await self.get_account_info(use_cache=False)
        positions = await self.get_positions()

        gross_exposure = 0.0
        net_exposure = 0.0
        for pos in positions:
            px = pos.market_price if pos.market_price is not None else pos.avg_cost
            notional = float(pos.market_value) if pos.market_value is not None else float(pos.quantity * px)
            signed_notional = -notional if str(pos.side).upper() == "SELL" else notional
            gross_exposure += abs(notional)
            net_exposure += signed_notional

        open_pnl: float | None
        if account.unrealized_pnl is not None:
            open_pnl = float(account.unrealized_pnl)
        else:
            pnl_vals = [float(p.unrealized_pnl) for p in positions if p.unrealized_pnl is not None]
            open_pnl = sum(pnl_vals) if pnl_vals else None

        closed_pnl, closed_pnl_source = await self._derive_closed_pnl_from_fill_events()

        with SessionLocal() as session:
            svc = PnlService(session)
            row = svc.record_snapshot(
                PnlSnapshotInput(
                    equity=float(account.net_liquidation) if account.net_liquidation is not None else None,
                    cash=float(account.cash_balance) if account.cash_balance is not None else None,
                    gross_exposure=gross_exposure,
                    net_exposure=net_exposure,
                    open_pnl=open_pnl,
                    closed_pnl=closed_pnl,
                    metadata_json={
                        "source": source,
                        "account_id": account_id,
                        "broker_mode": broker_mode,
                        "closed_pnl_source": closed_pnl_source,
                        "position_count": len(positions),
                        "currency": account.currency,
                    },
                )
            )
            session.commit()

        return {
            "snapshot_ts": row.snapshot_ts.isoformat(),
            "equity": row.equity,
            "cash": row.cash,
            "gross_exposure": row.gross_exposure,
            "net_exposure": row.net_exposure,
            "open_pnl": row.open_pnl,
            "closed_pnl": row.closed_pnl,
            "closed_pnl_source": closed_pnl_source,
            "source": source,
            "account_id": account_id,
            "broker_mode": broker_mode,
            "position_count": len(positions),
        }

    async def capture_pnl_snapshot(self) -> dict[str, Any]:
        """Backward-compatible MH-45 alias for manual snapshot capture."""
        return await self.capture_daily_pnl_snapshot(source="manual")

    async def submit_order(
        self,
        request: OrderRequest,
        *,
        decision_metadata: dict[str, Any] | None = None,
    ) -> OrderResult:
        return await self._submit_order_for_intent(
            request,
            intent="manual",
            decision_metadata=decision_metadata,
        )

    async def submit_auto_order(
        self,
        request: OrderRequest,
        *,
        decision_metadata: dict[str, Any] | None = None,
    ) -> OrderResult:
        """First auto-trading broker submission seam.

        Auto trading remains blocked by default, but this path must share the
        same broker submit safety gate as manual paper submit when later enabled.
        """
        return await self._submit_order_for_intent(
            request,
            intent="auto",
            decision_metadata=decision_metadata,
        )

    async def _submit_order_for_intent(
        self,
        request: OrderRequest,
        *,
        intent: str,
        decision_metadata: dict[str, Any] | None = None,
    ) -> OrderResult:
        """Submit an order to the broker.

        Args:
            request: Order details (ticker, side, quantity, order_type, etc.).

        Returns:
            OrderResult with broker_order_id and status.

        Raises:
            ValueError: If order request is invalid.
        """
        self._raise_for_invalid_order_request(request)

        try:
            assert_order_submission_allowed(intent=intent)
        except (
            AutoTradingBlockedError,
            LiveExecutionBlockedError,
            LiveTradingNotArmedError,
            TradingControlError,
            TradingControlMisconfiguredError,
        ) as exc:
            blocked_decision = self._build_blocked_error_decision(
                code="mode_guard_blocked",
                message=str(exc),
            )
            self._persist_submit_decision(
                intent=intent,
                preflight_decision=blocked_decision,
                warnings=[],
                source="submit_attempt",
                submit_gate="blocked",
                decision_metadata=decision_metadata,
            )
            raise

        trading_mode = str(get_broker_mode_metadata().get("mode") or "paper").lower()
        if trading_mode == "paper":
            try:
                portfolio_context = await self._build_submit_portfolio_context(request)
                preflight_result = self.dry_run_order(
                    request,
                    portfolio_context=portfolio_context,
                    persist_decision=True,
                    decision_source="submit_preflight",
                    intent=intent,
                    decision_metadata=decision_metadata,
                )
                preflight_decision = dict(preflight_result["preflight_decision"])
            except Exception as exc:
                preflight_decision = self._build_blocked_error_decision(
                    code="preflight_evaluation_error",
                    message=f"preflight evaluation failed: {exc}",
                )
                self._persist_submit_decision(
                    intent=intent,
                    preflight_decision=preflight_decision,
                    warnings=[],
                    source="submit_preflight",
                    submit_gate="blocked",
                    decision_metadata=decision_metadata,
                )
                self._persist_submit_decision(
                    intent=intent,
                    preflight_decision=preflight_decision,
                    warnings=[],
                    source="submit_attempt",
                    submit_gate="blocked",
                    decision_metadata=decision_metadata,
                )
                preflight_decision["submit_gate"] = "blocked"
                raise PaperPreflightBlockedError(
                    preflight_decision=preflight_decision,
                    preflight_context={},
                )

            if self._is_submit_blocked_by_preflight(preflight_decision):
                preflight_decision["submit_gate"] = "blocked"
                self._persist_submit_decision(
                    intent=intent,
                    preflight_decision=preflight_decision,
                    warnings=list(preflight_result.get("warnings") or []),
                    source="submit_attempt",
                    submit_gate="blocked",
                    decision_metadata=decision_metadata,
                )
                raise PaperPreflightBlockedError(
                    preflight_decision=preflight_decision,
                    preflight_context=preflight_result["preflight_context"],
                )

        await self.ensure_connected()
        assert self._broker is not None
        
        result = await self._broker.submit_order(request)

        allowed_decision = {
            "decision_status": "allowed",
            "submit_gate": "allowed",
            "advisory_count": 0,
            "would_block_count": 0,
            "blocking_count": 0,
            "advisory_items": [],
            "would_block_items": [],
            "blocking_items": [],
        }
        self._persist_submit_decision(
            intent=intent,
            preflight_decision=allowed_decision,
            warnings=[],
            source="submit_attempt",
            submit_gate="allowed",
            broker_order_id=result.broker_order_id,
            decision_metadata=decision_metadata,
        )
        
        if result.status == "REJECTED":
            _logger.warning(
                "Order rejected for %s: %s",
                request.ticker,
                result.error_message,
            )
        else:
            _logger.info(
                "Order %s submitted: %s %d %s @ %s",
                result.broker_order_id,
                request.side,
                request.quantity,
                request.ticker,
                request.limit_price or "MARKET",
            )
        
        return result

    async def _build_submit_portfolio_context(self, request: OrderRequest) -> dict[str, Any]:
        """Build live paper-account context for MH-78 submit preflight enforcement."""
        account = await self.get_account_info(use_cache=False)
        positions = await self.get_positions()
        daily_pnl = self.get_daily_pnl()

        current_symbol_exposure = 0.0
        current_total_exposure = 0.0
        open_position_count = 0

        for position in positions:
            px = position.market_price if position.market_price is not None else position.avg_cost
            notional = float(position.market_value) if position.market_value is not None else float(position.quantity * px)
            exposure = abs(notional)
            if position.quantity != 0:
                open_position_count += 1
            current_total_exposure += exposure
            if position.ticker.upper() == request.ticker.upper():
                current_symbol_exposure += exposure

        return {
            "cash_balance": float(account.cash_balance) if account.cash_balance is not None else None,
            "buying_power": float(account.buying_power) if account.buying_power is not None else None,
            "open_position_count": open_position_count,
            "current_symbol_exposure": current_symbol_exposure,
            "current_total_exposure": current_total_exposure,
            "daily_pnl": daily_pnl.get("daily_pnl"),
            "daily_loss": daily_pnl.get("daily_loss"),
        }

    def _collect_order_request_issues(self, request: OrderRequest) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []

        if request.quantity <= 0:
            issues.append(
                {
                    "code": "invalid_quantity",
                    "message": "Quantity must be > 0",
                }
            )

        if request.side not in ("BUY", "SELL"):
            issues.append(
                {
                    "code": "invalid_side",
                    "message": f"Invalid side: {request.side}",
                }
            )

        valid_order_types = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAIL"}
        if request.order_type not in valid_order_types:
            issues.append(
                {
                    "code": "invalid_order_type",
                    "message": f"Invalid order_type: {request.order_type}",
                }
            )

        if request.order_type in {"LIMIT", "STOP_LIMIT"} and request.limit_price is None:
            issues.append(
                {
                    "code": "missing_limit_price",
                    "message": "limit_price is required for LIMIT and STOP_LIMIT orders",
                }
            )

        if request.order_type in {"STOP", "STOP_LIMIT"} and request.stop_price is None:
            issues.append(
                {
                    "code": "missing_stop_price",
                    "message": "stop_price is required for STOP and STOP_LIMIT orders",
                }
            )

        return issues

    def _raise_for_invalid_order_request(self, request: OrderRequest) -> None:
        issues = self._collect_order_request_issues(request)
        if issues:
            raise ValueError(issues[0]["message"])

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an open order by broker order ID."""
        await self.ensure_connected()
        assert self._broker is not None
        success = await self._broker.cancel_order(broker_order_id)
        if success:
            _logger.info("Order %s cancelled", broker_order_id)
        else:
            _logger.warning("Failed to cancel order %s", broker_order_id)
        return success

    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]:
        """Poll order status by broker order ID."""
        await self.ensure_connected()
        assert self._broker is not None
        status = await self._broker.get_order_status(broker_order_id)
        return status

    async def reconcile_positions(
        self, expected_positions: dict[str, Decimal]
    ) -> dict[str, Any]:
        """Reconcile broker positions against expected state.

        Args:
            expected_positions: Map of ticker -> expected_quantity.

        Returns:
            Reconciliation report with mismatches and summary.
        """
        actual = await self.get_positions()
        actual_map = {p.ticker: p.quantity for p in actual}
        
        mismatches = {}
        for ticker, expected_qty in expected_positions.items():
            actual_qty = actual_map.get(ticker, Decimal("0"))
            if actual_qty != expected_qty:
                mismatches[ticker] = {
                    "expected": str(expected_qty),
                    "actual": str(actual_qty),
                    "delta": str(actual_qty - expected_qty),
                }
        
        return {
            "matched_count": len(expected_positions) - len(mismatches),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
            "actual_positions": actual,
        }

    def get_mode_metadata(self) -> dict[str, object]:
        """Return current broker mode metadata (broker, mode, live_execution_enabled, paper_trading_enabled)."""
        return get_broker_mode_metadata()

    def get_daily_pnl(self) -> dict[str, Any]:
        """Return today's P&L summary from pnl_snapshots (MH-43).

        Reads all pnl_snapshot rows where snapshot_ts >= UTC midnight today.
        Never contacts the broker directly and never mutates the database.

        Calculation rules:
        - closed_pnl  : sum of closed_pnl across all today's rows (realised fills).
        - open_pnl    : open_pnl from the most-recent row today (latest mark-to-market).
        - total_pnl   : closed_pnl + open_pnl.
        - daily_pnl   : same as total_pnl (primary field for dry-run context).
        - daily_loss  : abs(daily_pnl) when daily_pnl < 0, otherwise 0.0.

        When no rows exist for today all numeric fields are None and a note is
        included explaining the absence.  This method never raises for empty data.
        """
        from datetime import date, timezone

        from app.db.models.pnl_snapshot import PnlSnapshot

        today_date = date.today()
        today_midnight_utc = datetime.combine(today_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        today_str = today_date.isoformat()

        with SessionLocal() as session:
            rows = (
                session.query(PnlSnapshot)
                .filter(PnlSnapshot.snapshot_ts >= today_midnight_utc)
                .order_by(PnlSnapshot.snapshot_ts.asc())
                .all()
            )

        if not rows:
            return {
                "date": today_str,
                "daily_pnl": None,
                "daily_loss": None,
                "closed_pnl": None,
                "open_pnl": None,
                "total_pnl": None,
                "latest_snapshot_ts": None,
                "snapshot_count": 0,
                "source": "pnl_snapshots",
                "note": "No P&L snapshots available for today.",
            }

        # closed_pnl: sum of all realised fills today (nulls treated as 0)
        closed_pnl_total = sum(
            float(r.closed_pnl) for r in rows if r.closed_pnl is not None
        )
        closed_pnl: float | None = closed_pnl_total if any(
            r.closed_pnl is not None for r in rows
        ) else None

        # open_pnl: latest mark-to-market from the most recent row
        latest_row = rows[-1]
        open_pnl: float | None = (
            float(latest_row.open_pnl) if latest_row.open_pnl is not None else None
        )

        # total_pnl combines both; None only when both are absent
        if closed_pnl is not None or open_pnl is not None:
            total_pnl = (closed_pnl or 0.0) + (open_pnl or 0.0)
        else:
            total_pnl = None

        daily_pnl = total_pnl
        daily_loss: float | None
        if daily_pnl is not None:
            daily_loss = abs(daily_pnl) if daily_pnl < 0 else 0.0
        else:
            daily_loss = None

        return {
            "date": today_str,
            "daily_pnl": daily_pnl,
            "daily_loss": daily_loss,
            "closed_pnl": closed_pnl,
            "open_pnl": open_pnl,
            "total_pnl": total_pnl,
            "latest_snapshot_ts": latest_row.snapshot_ts.isoformat(),
            "snapshot_count": len(rows),
            "source": "pnl_snapshots",
            "note": None,
        }

    def dry_run_order(
        self,
        request: OrderRequest,
        portfolio_context: dict[str, Any] | None = None,
        *,
        persist_decision: bool = False,
        decision_source: str = "dry_run",
        intent: str = "manual",
        decision_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify whether an order would be accepted without submitting it.

        This method performs guard + request validation and advisory preflight
        checks only. It never calls broker adapter execution methods.

        Args:
            request: Order details for validation.
            portfolio_context: Optional caller-supplied account/portfolio state used to
                compute post-trade exposure estimates and enrich advisory warnings.
                Keys: cash_balance, buying_power, open_position_count,
                current_symbol_exposure, current_total_exposure, daily_pnl, daily_loss.
                Providing context never changes dry-run status — advisory only.
        """
        issues: list[dict[str, str]] = []
        warnings: list[dict[str, Any]] = []

        mode_guard_ok = True
        try:
            assert_order_submission_allowed(intent="manual", dry_run=True)
        except (
            AutoTradingBlockedError,
            LiveExecutionBlockedError,
            LiveTradingNotArmedError,
            TradingControlError,
            TradingControlMisconfiguredError,
        ) as exc:
            mode_guard_ok = False
            issues.append(
                {
                    "code": "mode_guard_blocked",
                    "message": str(exc),
                }
            )

        issues.extend(self._collect_order_request_issues(request))

        request_valid = not any(issue["code"] != "mode_guard_blocked" for issue in issues)

        if not mode_guard_ok:
            status = "blocked"
        elif request_valid:
            status = "ready"
        else:
            status = "invalid"

        estimated_notional: float | None = None
        if request.quantity > 0 and request.limit_price is not None:
            estimated_notional = float(request.quantity * request.limit_price)

        preflight_warnings, preflight_data = self._collect_preflight_warnings(
            request, estimated_notional, portfolio_context
        )
        warnings.extend(preflight_warnings)
        preflight_decision = self._build_preflight_decision(issues=issues, warnings=warnings)

        result = {
            "status": status,
            "mode_guard_ok": mode_guard_ok,
            "request_valid": request_valid,
            "estimated_notional": estimated_notional,
            "issues": issues,
            "warnings": warnings,
            "preflight_decision": preflight_decision,
            "preflight_context": preflight_data,
            "broker_mode": get_broker_mode_metadata(),
        }

        if persist_decision:
            self._persist_submit_decision_from_result(
                result=result,
                intent=intent,
                source=decision_source,
                decision_metadata=decision_metadata,
            )

        return result

    def _build_preflight_decision(
        self,
        *,
        issues: list[dict[str, Any]],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._preflight_decisions.build_preflight_decision(
            issues=issues,
            warnings=warnings,
        )

    def _is_submit_blocked_by_preflight(self, decision: dict[str, Any]) -> bool:
        return self._preflight_decisions.is_submit_blocked_by_preflight(decision)

    def _build_blocked_error_decision(self, *, code: str, message: str) -> dict[str, Any]:
        return self._preflight_decisions.build_blocked_error_decision(code=code, message=message)

    def _decision_reason_fields(
        self, preflight_decision: dict[str, Any], warnings: list[dict[str, Any]]
    ) -> tuple[str | None, str | None, str | None, list[dict[str, Any]]]:
        return self._preflight_decisions.decision_reason_fields(preflight_decision, warnings)

    def _execution_mode_metadata(self) -> tuple[str, str]:
        return self._preflight_decisions.execution_mode_metadata()

    def _persist_submit_decision(
        self,
        *,
        intent: str,
        preflight_decision: dict[str, Any],
        warnings: list[dict[str, Any]],
        source: str,
        submit_gate: str,
        broker_order_id: str | None = None,
        decision_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._preflight_decisions.persist_submit_decision(
            intent=intent,
            preflight_decision=preflight_decision,
            warnings=warnings,
            source=source,
            submit_gate=submit_gate,
            broker_order_id=broker_order_id,
            decision_metadata=decision_metadata,
        )

    def _persist_submit_decision_from_result(
        self,
        *,
        result: dict[str, Any],
        intent: str,
        source: str,
        decision_metadata: dict[str, Any] | None = None,
    ) -> None:
        self._preflight_decisions.persist_submit_decision_from_result(
            result=result,
            intent=intent,
            source=source,
            decision_metadata=decision_metadata,
        )

    def _collect_preflight_warnings(
        self,
        request: OrderRequest,
        estimated_notional: float | None,
        portfolio_context: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return self._preflight_advisory.collect_preflight_warnings(
            request,
            estimated_notional,
            portfolio_context,
        )
