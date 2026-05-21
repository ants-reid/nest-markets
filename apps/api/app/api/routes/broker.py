"""Broker endpoints — order execution, account, positions."""
import logging
from decimal import Decimal

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.clients.broker.broker_interface import OrderRequest
from app.config import get_settings
from app.schemas.broker_schemas import (
    BrokerDailyPnlSchema,
    BrokerPnlSnapshotCaptureSchema,
    BrokerTradeNormalizationResultSchema,
    BrokerTradeEventAuditTrailSchema,
    BrokerOrderAuditEntrySchema,
    BrokerOrderAuditTrailSchema,
    BrokerHealthSchema,
    BrokerModeSchema,
    TradingControlSchema,
    OrderDryRunIssueSchema,
    OrderDryRunPreflightDecisionSchema,
    OrderDryRunPreflightContextSchema,
    OrderDryRunRequestSchema,
    OrderDryRunResultSchema,
    OrderRequestSchema,
    OrderResultSchema,
    RiskLimitSnapshotSchema,
    AccountInfoSchema,
    PositionInfoSchema,
    ReconciliationReportSchema,
)
from app.services import audit_log_service
from app.services.broker_mode_guard import (
    BrokerModeInconsistencyError,
    LiveExecutionBlockedError,
    check_ibkr_gateway,
    get_broker_mode_metadata,
    is_live_mode_enabled,
    is_paper_account_id,
)
from app.services.broker_service import BrokerService
from app.services.broker_service import PaperPreflightBlockedError
from app.services.trading_control_service import (
    AutoTradingBlockedError,
    LiveTradingNotArmedError,
    TradingControlError,
    TradingControlMisconfiguredError,
    assert_mode_configuration_consistent,
    get_trading_mode,
)

router = APIRouter(prefix="/broker", tags=["broker"])
_logger = logging.getLogger(__name__)

# Global broker service instance (in production, use dependency injection)
_broker_service: BrokerService | None = None


def get_broker_service() -> BrokerService:
    """Get or create the global broker service instance."""
    global _broker_service
    if _broker_service is None:
        _broker_service = BrokerService()
    return _broker_service


def _is_broker_transport_error(exc: Exception) -> bool:
    return isinstance(exc, httpx.TransportError)


def _paper_fallback_account_info() -> AccountInfoSchema:
    meta = get_broker_mode_metadata()
    return AccountInfoSchema(
        net_liquidation=0.0,
        cash_balance=0.0,
        buying_power=0.0,
        currency="USD",
        excess_liquidity=0.0,
        margin=0.0,
        unrealized_pnl=0.0,
        broker_mode=BrokerModeSchema(**meta),
    )


@router.get("/mode", response_model=BrokerModeSchema)
async def get_broker_mode():
    """Return current broker mode status (paper/live isolation metadata)."""
    meta = get_broker_mode_metadata()
    return BrokerModeSchema(**meta)


@router.get("/control", response_model=TradingControlSchema)
async def get_broker_control():
    """Return the env-backed trading control state for MH-36B."""
    state = get_trading_mode()
    return TradingControlSchema(
        trading_mode=state.trading_mode,
        execution_control=state.execution_control,
        arming_state=state.arming_state,
        live_order_submission_allowed=state.live_order_submission_allowed,
        paper_order_submission_allowed=state.paper_order_submission_allowed,
        auto_trading_allowed=state.auto_trading_allowed,
        emergency_stop_active=state.emergency_stop_active,
        reasons=list(state.reasons),
    )


@router.get("/health", response_model=BrokerHealthSchema)
async def get_broker_health():
    """Runtime health check for the IBKR broker setup (paper or live).

    Checks (in order):
    1. Mode guard — env vars must be consistent (either all-paper or all-live).
    2. Gateway reachability — lightweight probe to /iserver/auth/status.
    3. Account type — matches configured IBKR account ID.

    Returns 200 in all cases; inspect the ``status`` field to determine readiness:
    - ``paper_ready``       — all checks pass, paper mode configured.
    - ``live_ready``        — all checks pass, live mode configured (REAL MONEY).
    - ``paper_config_only`` — guard OK but gateway not yet reachable (paper mode).
    - ``live_config_only``  — guard OK but gateway not yet reachable (live mode, REAL MONEY).
    - ``misconfigured``     — env vars are mismatched; orders will be rejected.
    """
    settings = get_settings()

    # 1. Mode guard check
    mode_guard_ok = True
    try:
        assert_mode_configuration_consistent()
    except (BrokerModeInconsistencyError, TradingControlMisconfiguredError):
        mode_guard_ok = False

    # 2. Gateway reachability probe (short timeout — non-blocking for callers)
    gateway_reachable = await check_ibkr_gateway(settings.ibkr_gateway_url, timeout=5.0)

    # 3. Account type from configured account ID
    account_id = settings.ibkr_account_id or ""
    account_is_paper = is_paper_account_id(account_id)

    # Determine mode
    live_enabled = is_live_mode_enabled()

    # Overall status
    if not mode_guard_ok:
        status = "misconfigured"
    elif live_enabled:
        # Live mode
        status = "live_ready" if gateway_reachable else "live_config_only"
    else:
        # Paper mode
        status = "paper_ready" if gateway_reachable else "paper_config_only"

    meta = get_broker_mode_metadata()
    return BrokerHealthSchema(
        status=status,
        mode_guard_ok=mode_guard_ok,
        gateway_reachable=gateway_reachable,
        gateway_url=settings.ibkr_gateway_url,
        account_id=account_id,
        account_is_paper=account_is_paper,
        broker_mode=BrokerModeSchema(**meta),
    )


@router.get("/account", response_model=AccountInfoSchema)
async def get_account():
    """Get account balance summary."""
    try:
        service = get_broker_service()
        info = await service.get_account_info()
        meta = get_broker_mode_metadata()
        return AccountInfoSchema(
            net_liquidation=float(info.net_liquidation),
            cash_balance=float(info.cash_balance),
            buying_power=float(info.buying_power),
            currency=info.currency,
            excess_liquidity=float(info.excess_liquidity),
            margin=float(info.margin),
            unrealized_pnl=float(info.unrealized_pnl),
            broker_mode=BrokerModeSchema(**meta),
        )
    except Exception as exc:
        if not is_live_mode_enabled() and _is_broker_transport_error(exc):
            _logger.info("Broker account unavailable in paper mode; returning empty snapshot: %s", exc)
            return _paper_fallback_account_info()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise


@router.get("/positions", response_model=list[PositionInfoSchema])
async def get_positions():
    """Get all open positions."""
    try:
        service = get_broker_service()
        positions = await service.get_positions()
        return [
            PositionInfoSchema(
                conid=p.conid,
                ticker=p.ticker,
                side=p.side,
                quantity=float(p.quantity),
                avg_cost=float(p.avg_cost),
                market_price=float(p.market_price) if p.market_price else None,
                market_value=float(p.market_value) if p.market_value else None,
                unrealized_pnl=float(p.unrealized_pnl) if p.unrealized_pnl else None,
                asset_class=p.asset_class,
                currency=p.currency,
            )
            for p in positions
        ]
    except Exception as exc:
        if not is_live_mode_enabled() and _is_broker_transport_error(exc):
            _logger.info("Broker positions unavailable in paper mode; returning empty list: %s", exc)
            return []
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise


@router.get("/daily-pnl", response_model=BrokerDailyPnlSchema)
def get_daily_pnl():
    """Return today's P&L summary from pnl_snapshots (MH-43).

    Read-only endpoint — never contacts the broker directly.
    Returns safe empty response (nulls + note) when no snapshots exist for today.
    Not gated by live-mode config; always accessible.
    """
    try:
        service = get_broker_service()
        data = service.get_daily_pnl()
        return BrokerDailyPnlSchema(**data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/daily-pnl/snapshot", response_model=BrokerPnlSnapshotCaptureSchema)
async def capture_daily_pnl_snapshot():
    """Capture one P&L snapshot from current broker account + positions (MH-45).

    Writes a single row to `pnl_snapshots` and returns the captured values.
    This endpoint is ingestion-only and does not affect order submission behavior.
    """
    try:
        service = get_broker_service()
        data = await service.capture_daily_pnl_snapshot(source="manual")
        return BrokerPnlSnapshotCaptureSchema(**data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/daily-pnl/snapshot/scheduled", response_model=BrokerPnlSnapshotCaptureSchema)
async def capture_daily_pnl_snapshot_scheduled():
    """Capture one scheduled P&L snapshot for the active broker account only (MH-46A)."""
    try:
        service = get_broker_service()
        data = await service.capture_daily_pnl_snapshot(source="scheduled")
        return BrokerPnlSnapshotCaptureSchema(**data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/trades/normalize", response_model=BrokerTradeNormalizationResultSchema)
async def normalize_broker_trades():
    """Normalize and stage broker trade/fill events (MH-47).

    Ingestion/reconciliation endpoint only. Does not submit orders or alter
    trading controls.
    """
    try:
        service = get_broker_service()
        data = await service.normalize_and_stage_trade_events(source="broker_account_trades")
        return BrokerTradeNormalizationResultSchema(**data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/trades/normalized", response_model=BrokerTradeEventAuditTrailSchema)
async def get_normalized_broker_trades(limit: int = Query(default=100, ge=1, le=500)):
    """Return normalized broker trade/fill events for provenance audit readback (MH-47B)."""
    try:
        service = get_broker_service()
        data = service.get_normalized_trade_events(limit=limit)
        return BrokerTradeEventAuditTrailSchema(**data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/orders", response_model=OrderResultSchema)
async def submit_order(request: OrderRequestSchema):
    """Submit an order to the broker."""
    try:
        service = get_broker_service()

        order_request = OrderRequest(
            ticker=request.ticker,
            side=request.side,
            quantity=Decimal(str(request.quantity)),
            order_type=request.order_type,
            limit_price=Decimal(str(request.limit_price)) if request.limit_price else None,
            stop_price=Decimal(str(request.stop_price)) if request.stop_price else None,
            tif=request.tif,
            outside_rth=request.outside_rth,
            client_order_id=request.client_order_id,
        )

        result = await service.submit_order(order_request)
        audit_log_service.log_broker_order_event(
            action="submit",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status=result.status,
            broker_order_id=result.broker_order_id,
            reason=result.error_message,
            dry_run=False,
        )
        meta = get_broker_mode_metadata()
        return OrderResultSchema(
            broker_order_id=result.broker_order_id,
            status=result.status,
            filled_price=float(result.filled_price) if result.filled_price else None,
            filled_quantity=float(result.filled_quantity) if result.filled_quantity else None,
            error_message=result.error_message,
            broker_mode=BrokerModeSchema(**meta),
        )
    except HTTPException:
        raise
    except PaperPreflightBlockedError as exc:
        audit_log_service.log_broker_order_event(
            action="submit",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status="BLOCKED",
            reason=str(exc),
            dry_run=False,
        )
        raise HTTPException(status_code=403, detail=exc.to_response_detail()) from exc
    except (
        AutoTradingBlockedError,
        LiveExecutionBlockedError,
        LiveTradingNotArmedError,
        BrokerModeInconsistencyError,
        TradingControlError,
        TradingControlMisconfiguredError,
    ) as exc:
        audit_log_service.log_broker_order_event(
            action="submit",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status="BLOCKED",
            reason=str(exc),
            dry_run=False,
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        audit_log_service.log_broker_order_event(
            action="submit",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status="INVALID",
            reason=str(exc),
            dry_run=False,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        audit_log_service.log_broker_order_event(
            action="submit",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status="ERROR",
            reason=str(exc),
            dry_run=False,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/orders/dry-run", response_model=OrderDryRunResultSchema)
async def dry_run_order(request: OrderDryRunRequestSchema):
    """Verify an order request without submitting anything to the broker.

    This endpoint is used for operator safety checks before paper execution.
    It runs the paper-mode guard and order validation only.

    Optionally accepts portfolio context fields (cash_balance, buying_power,
    open_position_count, current_symbol_exposure, current_total_exposure,
    daily_pnl, daily_loss) to enrich the preflight_context in the response.
    Providing context never affects dry-run status — advisory only.
    """
    try:
        service = get_broker_service()

        order_request = OrderRequest(
            ticker=request.ticker,
            side=request.side,
            quantity=Decimal(str(request.quantity)),
            order_type=request.order_type,
            limit_price=Decimal(str(request.limit_price)) if request.limit_price else None,
            stop_price=Decimal(str(request.stop_price)) if request.stop_price else None,
            tif=request.tif,
            outside_rth=request.outside_rth,
            client_order_id=request.client_order_id,
        )

        portfolio_context: dict | None = None
        _ctx_fields = (
            "cash_balance", "buying_power", "open_position_count",
            "current_symbol_exposure", "current_total_exposure",
            "daily_pnl", "daily_loss",
        )
        raw_ctx = {k: getattr(request, k) for k in _ctx_fields if getattr(request, k) is not None}
        if raw_ctx:
            portfolio_context = raw_ctx

        result = service.dry_run_order(order_request, portfolio_context=portfolio_context)
        audit_log_service.log_broker_order_event(
            action="dry_run",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status=result["status"],
            reason=None,
            dry_run=True,
            issues=result["issues"],
        )

        preflight_ctx_data = result.get("preflight_context") or {}
        snapshot_data = preflight_ctx_data.get("risk_limit_snapshot")
        preflight_context_schema = OrderDryRunPreflightContextSchema(
            cash_balance=preflight_ctx_data.get("cash_balance"),
            buying_power=preflight_ctx_data.get("buying_power"),
            open_position_count=preflight_ctx_data.get("open_position_count"),
            current_symbol_exposure=preflight_ctx_data.get("current_symbol_exposure"),
            estimated_post_trade_symbol_exposure=preflight_ctx_data.get("estimated_post_trade_symbol_exposure"),
            current_total_exposure=preflight_ctx_data.get("current_total_exposure"),
            estimated_post_trade_total_exposure=preflight_ctx_data.get("estimated_post_trade_total_exposure"),
            daily_pnl=preflight_ctx_data.get("daily_pnl"),
            daily_loss=preflight_ctx_data.get("daily_loss"),
            risk_limit_snapshot=RiskLimitSnapshotSchema(**snapshot_data) if snapshot_data else None,
        )

        return OrderDryRunResultSchema(
            status=result["status"],
            mode_guard_ok=result["mode_guard_ok"],
            request_valid=result["request_valid"],
            estimated_notional=result["estimated_notional"],
            issues=[OrderDryRunIssueSchema(**issue) for issue in result["issues"]],
            warnings=[OrderDryRunIssueSchema(**warning) for warning in result.get("warnings", [])],
            preflight_decision=OrderDryRunPreflightDecisionSchema(**result["preflight_decision"]),
            preflight_context=preflight_context_schema,
            broker_mode=BrokerModeSchema(**result["broker_mode"]),
        )
    except HTTPException:
        raise
    except ValueError as exc:
        audit_log_service.log_broker_order_event(
            action="dry_run",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status="invalid",
            reason=str(exc),
            dry_run=True,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        audit_log_service.log_broker_order_event(
            action="dry_run",
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            status="error",
            reason=str(exc),
            dry_run=True,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/orders/audit", response_model=BrokerOrderAuditTrailSchema)
async def get_order_audit_trail(limit: int = 50):
    """Return recent append-only broker order audit events."""
    entries = audit_log_service.list_broker_order_events(limit=limit)
    return BrokerOrderAuditTrailSchema(
        entries=[BrokerOrderAuditEntrySchema(**entry) for entry in entries],
    )


@router.delete("/orders/{broker_order_id}")
async def cancel_order(broker_order_id: str):
    """Cancel an open order."""
    try:
        service = get_broker_service()
        success = await service.cancel_order(broker_order_id)
        if not success:
            raise HTTPException(status_code=404, detail="Order not found or already cancelled")
        return {"success": True, "broker_order_id": broker_order_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/orders/{broker_order_id}/status")
async def get_order_status(broker_order_id: str):
    """Get order status by broker order ID."""
    try:
        service = get_broker_service()
        status = await service.get_order_status(broker_order_id)
        return status
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/reconcile", response_model=ReconciliationReportSchema)
async def reconcile_positions(expected_positions: dict[str, float]):
    """Reconcile broker positions against expected state."""
    try:
        service = get_broker_service()

        expected = {
            ticker: Decimal(str(qty))
            for ticker, qty in expected_positions.items()
        }

        report = await service.reconcile_positions(expected)

        # Convert PositionInfo objects to dicts for JSON serialization
        actual_positions_data = [
            {
                "conid": p.conid,
                "ticker": p.ticker,
                "side": p.side,
                "quantity": float(p.quantity),
                "avg_cost": float(p.avg_cost),
                "market_price": float(p.market_price) if p.market_price else None,
                "asset_class": p.asset_class,
                "currency": p.currency,
            }
            for p in report["actual_positions"]
        ]

        return ReconciliationReportSchema(
            matched_count=report["matched_count"],
            mismatch_count=report["mismatch_count"],
            mismatches=report["mismatches"],
            actual_positions=actual_positions_data,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
