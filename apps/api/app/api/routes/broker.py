"""Broker endpoints — order execution, account, positions."""
import asyncio
import logging
from typing import Any
from decimal import Decimal
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from app.clients.broker.broker_interface import OrderRequest
from app.clients.broker.tws_adapter import TwsConnectionUnavailableError
from app.config import get_settings
from app.schemas.broker_schemas import (
    BrokerDailyPnlSchema,
    BrokerPnlSnapshotCaptureSchema,
    BrokerTradeNormalizationResultSchema,
    BrokerTradeEventAuditTrailSchema,
    BrokerOrderAuditEntrySchema,
    BrokerOrderAuditTrailSchema,
    BrokerHealthWithReadinessSchema,
    BrokerReadinessChecklistItemSchema,
    BrokerReadinessChecklistSchema,
    BrokerModeSchema,
    SeriousPaperRouteCheckResponseSchema,
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
from app.services.paper_source_contract import broker_sources_from_mode
from app.services.serious_paper_routing_service import SeriousPaperRoutingService
from app.services.cockpit_auto_paper_status_service import get_auto_paper_status_card
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


async def _extract_submit_decision_metadata(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        return {}

    if not isinstance(payload, dict):
        return {}

    correlation_id = payload.get("submit_decision_correlation_id") or payload.get(
        "client_order_id"
    )
    return {
        "correlation_id": correlation_id,
        "recommendation_id": payload.get("recommendation_id"),
        "route_check_reference": payload.get("route_check_reference"),
        "dry_run_reference": payload.get("dry_run_reference"),
        "ticker": payload.get("ticker"),
        "side": payload.get("side"),
        "quantity": payload.get("quantity"),
        "order_type": payload.get("order_type"),
        "limit_price": payload.get("limit_price"),
        "stop_price": payload.get("stop_price"),
    }


def get_broker_service() -> BrokerService:
    """Get or create the global broker service instance."""
    global _broker_service
    if _broker_service is None:
        _broker_service = BrokerService()
    return _broker_service


def _dry_run_source_meta(meta: dict[str, object]) -> dict[str, object]:
    """Return canonical dry-run labels from the current runtime mode."""
    mode = str(meta.get("mode") or "paper").lower()
    if mode == "live":
        return {
            "execution_source": "broker_dry_run",
            "balance_source": "ibkr_live_locked",
            "fees_source": "unavailable",
            "fills_source": "pending_broker_fill",
            "positions_source": "ibkr_live_locked",
            "serious_paper_source": "ibkr_paper",
            "is_canonical_paper": False,
            "canonical_paper_route": "/broker/orders",
            "broker_account_mode": "live",
            "live_state": "ibkr_live_locked",
            "paper_path_note": "Dry-run stays available for contract inspection, but live submit remains locked.",
        }

    return {
        "execution_source": "broker_dry_run",
        "balance_source": "ibkr_paper",
        "fees_source": "pending_broker_report",
        "fills_source": "pending_broker_fill",
        "positions_source": "ibkr_paper",
        "serious_paper_source": "ibkr_paper",
        "is_canonical_paper": True,
        "canonical_paper_route": "/broker/orders",
        "broker_account_mode": "paper",
        "live_state": "ibkr_live_locked",
        "paper_path_note": "Dry-run validates the canonical IBKR paper submit path without placing an order.",
    }


def _is_broker_transport_error(exc: Exception) -> bool:
    return isinstance(exc, httpx.TransportError)


def _is_tws_unavailable_error(exc: Exception) -> bool:
    if isinstance(exc, TwsConnectionUnavailableError):
        return True
    message = str(exc).lower()
    return (
        "client id" in message
        or "already in use" in message
        or "peer closed connection" in message
        or "api connection failed" in message
        or "timeouterror" in message
    )


def _paper_fallback_account_info() -> AccountInfoSchema:
    meta = get_broker_mode_metadata()
    source_labels = broker_sources_from_mode(meta)
    return AccountInfoSchema(
        net_liquidation=0.0,
        cash_balance=0.0,
        buying_power=0.0,
        currency="USD",
        excess_liquidity=0.0,
        margin=0.0,
        unrealized_pnl=0.0,
        broker_mode=BrokerModeSchema(**meta),
        **source_labels,
    )


def _readiness_status_rank(value: str) -> int:
    if value == "red":
        return 2
    if value == "yellow":
        return 1
    return 0


def _build_readiness_item(
    *,
    key: str,
    label: str,
    status: str,
    reason: str,
    suggested_action: str,
) -> BrokerReadinessChecklistItemSchema:
    return BrokerReadinessChecklistItemSchema(
        key=key,
        label=label,
        status=status,
        reason=reason,
        suggested_action=suggested_action,
    )


async def _probe_broker_account_health(service: BrokerService) -> tuple[bool, bool, str]:
    try:
        await asyncio.wait_for(service.get_account_info(), timeout=8.0)
        return True, True, "IBKR account snapshot loaded."
    except Exception as exc:
        if not is_live_mode_enabled() and (
            isinstance(exc, asyncio.TimeoutError)
            or _is_broker_transport_error(exc)
            or _is_tws_unavailable_error(exc)
        ):
            return True, False, f"Account probe degraded in paper mode; fallback snapshot allowed ({exc})."
        return False, False, f"Account probe failed: {exc}"


async def _probe_broker_positions_health(service: BrokerService) -> tuple[bool, bool, str]:
    try:
        await asyncio.wait_for(service.get_positions(), timeout=8.0)
        return True, True, "IBKR positions snapshot loaded."
    except Exception as exc:
        if not is_live_mode_enabled() and (
            isinstance(exc, asyncio.TimeoutError)
            or _is_broker_transport_error(exc)
            or _is_tws_unavailable_error(exc)
        ):
            return True, False, f"Positions probe degraded in paper mode; empty fallback allowed ({exc})."
        return False, False, f"Positions probe failed: {exc}"


@router.get("/mode", response_model=BrokerModeSchema)
async def get_broker_mode():
    """Return current broker mode status (paper/live isolation metadata)."""
    meta = get_broker_mode_metadata()
    return BrokerModeSchema(**meta)


@router.get("/paper/canonical-route", response_model=SeriousPaperRouteCheckResponseSchema)
async def get_canonical_paper_route_check():
    """Return the read-only routing decision for intentional serious-paper workflows."""
    decision = SeriousPaperRoutingService().resolve_route()
    return SeriousPaperRouteCheckResponseSchema(
        requested_mode=decision.requested_mode,
        resolved_execution_source=decision.resolved_execution_source,
        resolved_route=decision.resolved_route,
        simulator_route=decision.simulator_route,
        simulator_allowed_for_serious_paper=decision.simulator_allowed_for_serious_paper,
        broker_account_mode_required=decision.broker_account_mode_required,
        current_broker_account_mode=decision.current_broker_account_mode,
        can_route_to_broker_paper=decision.can_route_to_broker_paper,
        blocked_reason=decision.blocked_reason,
        live_state=decision.live_state,
        would_block=decision.would_block,
        is_submit=decision.is_submit,
        next_required_action=decision.next_required_action,
        serious_paper_source=decision.serious_paper_source,
        canonical_paper_route=decision.canonical_paper_route,
        broker_mode=BrokerModeSchema(**decision.broker_mode),
    )


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


@router.get("/health", response_model=BrokerHealthWithReadinessSchema)
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
    service = get_broker_service()
    diagnostics = service.get_runtime_diagnostics()
    trading_state = get_trading_mode()

    account_ok, account_live, account_reason = await _probe_broker_account_health(service)
    positions_ok, positions_live, positions_reason = await _probe_broker_positions_health(service)

    tws_connected = str(diagnostics.get("tws_connection_state") or "").lower() == "connected"
    host_port_reachable = bool(gateway_reachable or tws_connected)
    contention_active = str(diagnostics.get("tws_last_error_code") or "") == "326" or (
        "already in use" in str(diagnostics.get("tws_last_error_message") or "").lower()
    )

    cockpit_card: dict[str, Any] | None = None
    try:
        cockpit_card = get_auto_paper_status_card()
    except Exception:
        cockpit_card = None

    paper_normal_mode_active = bool(
        (cockpit_card or {}).get("next_run_guidance", {}).get("paper_normal_mode_active")
    )
    audit_alignment_status = str((cockpit_card or {}).get("audit_alignment", {}).get("status") or "unknown").lower()
    candidate_queue_visible = isinstance((cockpit_card or {}).get("candidate_queue"), dict)
    latest_paper_order_visible = isinstance((cockpit_card or {}).get("latest_paper_order"), dict) or (
        "latest_paper_order" in (cockpit_card or {})
    )

    items: list[BrokerReadinessChecklistItemSchema] = []
    items.append(
        _build_readiness_item(
            key="broker_provider_tws",
            label="Broker provider is TWS",
            status="green" if str(meta.get("broker") or "").lower() == "tws" else "red",
            reason=f"Configured provider: {meta.get('broker')}",
            suggested_action="Set BROKER_PROVIDER=tws.",
        )
    )
    items.append(
        _build_readiness_item(
            key="broker_mode_paper",
            label="Broker mode is paper",
            status="green" if str(meta.get("mode") or "").lower() == "paper" else "red",
            reason=f"Configured mode: {meta.get('mode')}",
            suggested_action="Set BROKER_MODE=paper.",
        )
    )
    items.append(
        _build_readiness_item(
            key="live_execution_disabled",
            label="Live execution is disabled",
            status="green" if not bool(meta.get("live_execution_enabled")) else "red",
            reason=f"LIVE_EXECUTION_ENABLED={meta.get('live_execution_enabled')}",
            suggested_action="Set LIVE_EXECUTION_ENABLED=false.",
        )
    )
    items.append(
        _build_readiness_item(
            key="live_submit_blocked",
            label="Live order submission remains blocked",
            status="green" if not trading_state.live_order_submission_allowed else "red",
            reason=f"live_order_submission_allowed={trading_state.live_order_submission_allowed}",
            suggested_action="Keep trading control in paper/manual mode with live submits blocked.",
        )
    )
    items.append(
        _build_readiness_item(
            key="paper_trading_enabled",
            label="Paper trading is enabled",
            status="green" if bool(meta.get("paper_trading_enabled")) else "red",
            reason=f"paper_trading_enabled={meta.get('paper_trading_enabled')}",
            suggested_action="Set PAPER_TRADING_ENABLED=true.",
        )
    )
    items.append(
        _build_readiness_item(
            key="paper_submit_allowed",
            label="Paper order submission is allowed",
            status="green" if trading_state.paper_order_submission_allowed else "red",
            reason=f"paper_order_submission_allowed={trading_state.paper_order_submission_allowed}",
            suggested_action="Set trading control to allow paper submits.",
        )
    )
    items.append(
        _build_readiness_item(
            key="tws_enabled",
            label="TWS adapter is enabled",
            status="green" if settings.tws_enabled else "red",
            reason=f"TWS_ENABLED={settings.tws_enabled}",
            suggested_action="Set TWS_ENABLED=true.",
        )
    )
    items.append(
        _build_readiness_item(
            key="tws_reachable",
            label="TWS host/port is reachable",
            status="green" if host_port_reachable else "yellow",
            reason=(
                "Gateway probe reachable."
                if gateway_reachable
                else f"tws_connection_state={diagnostics.get('tws_connection_state') or 'unknown'}"
            ),
            suggested_action="Ensure TWS/Gateway is running and reachable at configured host/port.",
        )
    )
    items.append(
        _build_readiness_item(
            key="paper_account_visible",
            label="IBKR paper account DUP153837 is configured",
            status="green" if (account_id == "DUP153837" and account_is_paper) else "red",
            reason=f"account_id={account_id} account_is_paper={account_is_paper}",
            suggested_action="Set IBKR_ACCOUNT_ID=DUP153837.",
        )
    )
    items.append(
        _build_readiness_item(
            key="account_endpoint_healthy",
            label="Account endpoint is healthy",
            status="green" if account_ok else "red",
            reason=account_reason,
            suggested_action=(
                "No action needed."
                if account_live
                else "Check TWS connectivity; paper fallback is active until broker account responds."
            ),
        )
    )
    items.append(
        _build_readiness_item(
            key="positions_endpoint_healthy",
            label="Positions endpoint is healthy",
            status="green" if positions_ok else "red",
            reason=positions_reason,
            suggested_action=(
                "No action needed."
                if positions_live
                else "Check TWS connectivity; paper empty-list fallback is active until broker positions respond."
            ),
        )
    )
    items.append(
        _build_readiness_item(
            key="single_tws_client_owner",
            label="No duplicate backend TWS client owner detected",
            status="red" if contention_active else "green",
            reason=(
                f"tws_last_error_code={diagnostics.get('tws_last_error_code')}"
                if contention_active
                else "No client-id contention diagnostics detected."
            ),
            suggested_action="Restart duplicate API/TWS client processes and keep one backend owner for the configured client id.",
        )
    )
    items.append(
        _build_readiness_item(
            key="client_id_contention_inactive",
            label="TWS client-id contention is inactive",
            status="red" if contention_active else "green",
            reason=(
                diagnostics.get("tws_last_error_message") or "No contention message present."
            ),
            suggested_action="If contention appears, stop duplicate workers and reconnect with a single client id owner.",
        )
    )
    items.append(
        _build_readiness_item(
            key="auto_paper_enabled",
            label="Auto-paper mode is enabled",
            status="green" if settings.auto_paper_enabled else "yellow",
            reason=f"AUTO_PAPER_ENABLED={settings.auto_paper_enabled}",
            suggested_action="Set AUTO_PAPER_ENABLED=true for scheduled paper runs.",
        )
    )
    items.append(
        _build_readiness_item(
            key="paper_normal_mode_active",
            label="Paper Normal Mode is active",
            status="green" if paper_normal_mode_active else "yellow",
            reason=(
                "Cockpit guidance reports paper_normal_mode_active=true."
                if paper_normal_mode_active
                else "Cockpit guidance does not report Paper Normal Mode as active."
            ),
            suggested_action="Align paper mode, auto-paper enabled, and paper submission allowance.",
        )
    )
    items.append(
        _build_readiness_item(
            key="scheduler_visible",
            label="Scheduler state is visible",
            status="green",
            reason=(
                "AUTO_PAPER_BACKGROUND_SCHEDULER_ENABLED=true"
                if settings.auto_paper_background_scheduler_enabled
                else "AUTO_PAPER_BACKGROUND_SCHEDULER_ENABLED=false"
            ),
            suggested_action="Use /market-data/auto-paper/scheduler/status to inspect scheduler state.",
        )
    )
    items.append(
        _build_readiness_item(
            key="candidate_queue_visible",
            label="Candidate queue visibility is available",
            status="green" if candidate_queue_visible else "yellow",
            reason=(
                "candidate_queue payload is present in cockpit status."
                if candidate_queue_visible
                else "candidate_queue payload not present in cockpit status."
            ),
            suggested_action="Review candidate_queue in cockpit status before supervised runs.",
        )
    )
    items.append(
        _build_readiness_item(
            key="audit_alignment_visible",
            label="Audit alignment visibility is available",
            status=("green" if audit_alignment_status == "ok" else "yellow"),
            reason=(
                f"audit_alignment status is {audit_alignment_status}."
                if audit_alignment_status != "unknown"
                else "audit_alignment payload is unavailable."
            ),
            suggested_action="Inspect audit_alignment for warnings after each run.",
        )
    )
    items.append(
        _build_readiness_item(
            key="latest_paper_order_visible",
            label="Latest paper order visibility is available",
            status="green" if latest_paper_order_visible else "yellow",
            reason=(
                "latest_paper_order field is present in cockpit status."
                if latest_paper_order_visible
                else "latest_paper_order field is missing from cockpit status."
            ),
            suggested_action="Use cockpit latest_paper_order to track current order lifecycle state.",
        )
    )
    items.append(
        _build_readiness_item(
            key="clear_fix_text_present",
            label="Checklist provides clear fix text",
            status="green",
            reason="Every checklist item includes a suggested action.",
            suggested_action="No action needed.",
        )
    )

    overall_status = "green"
    if any(_readiness_status_rank(item.status) == 2 for item in items):
        overall_status = "red"
    elif any(_readiness_status_rank(item.status) == 1 for item in items):
        overall_status = "yellow"

    readiness = BrokerReadinessChecklistSchema(
        overall_status=overall_status,
        last_checked_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )
    return BrokerHealthWithReadinessSchema(
        status=status,
        mode_guard_ok=mode_guard_ok,
        gateway_reachable=gateway_reachable,
        gateway_url=settings.ibkr_gateway_url,
        account_id=account_id,
        account_is_paper=account_is_paper,
        broker_mode=BrokerModeSchema(**meta),
        tws_runtime_client_id=diagnostics.get("tws_runtime_client_id"),
        tws_connection_state=diagnostics.get("tws_connection_state"),
        tws_last_error_code=diagnostics.get("tws_last_error_code"),
        tws_last_error_message=diagnostics.get("tws_last_error_message"),
        broker_readiness=readiness,
    )


@router.get("/account", response_model=AccountInfoSchema)
async def get_account():
    """Get account balance summary."""
    try:
        service = get_broker_service()
        info = await asyncio.wait_for(service.get_account_info(), timeout=8.0)
        meta = get_broker_mode_metadata()
        source_labels = broker_sources_from_mode(meta)
        return AccountInfoSchema(
            net_liquidation=float(info.net_liquidation),
            cash_balance=float(info.cash_balance),
            buying_power=float(info.buying_power),
            currency=info.currency,
            excess_liquidity=float(info.excess_liquidity),
            margin=float(info.margin),
            unrealized_pnl=float(info.unrealized_pnl),
            broker_mode=BrokerModeSchema(**meta),
            **source_labels,
        )
    except Exception as exc:
        if not is_live_mode_enabled() and (
            isinstance(exc, asyncio.TimeoutError) or _is_broker_transport_error(exc)
        ):
            _logger.info("Broker account unavailable in paper mode; returning empty snapshot: %s", exc)
            return _paper_fallback_account_info()
        if not is_live_mode_enabled() and _is_tws_unavailable_error(exc):
            diagnostics = service.get_runtime_diagnostics()
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "tws_unavailable",
                    "message": str(exc),
                    "diagnostics": diagnostics,
                },
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise


@router.get("/positions", response_model=list[PositionInfoSchema])
async def get_positions():
    """Get all open positions."""
    try:
        service = get_broker_service()
        positions = await asyncio.wait_for(service.get_positions(), timeout=8.0)
        meta = get_broker_mode_metadata()
        source_labels = broker_sources_from_mode(meta)
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
                **source_labels,
            )
            for p in positions
        ]
    except Exception as exc:
        if not is_live_mode_enabled() and (
            isinstance(exc, asyncio.TimeoutError) or _is_broker_transport_error(exc)
        ):
            _logger.info("Broker positions unavailable in paper mode; returning empty list: %s", exc)
            return []
        if not is_live_mode_enabled() and _is_tws_unavailable_error(exc):
            diagnostics = service.get_runtime_diagnostics()
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "tws_unavailable",
                    "message": str(exc),
                    "diagnostics": diagnostics,
                },
            ) from exc
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
async def submit_order(request: OrderRequestSchema, raw_request: Request):
    """Submit an order to the broker."""
    try:
        service = get_broker_service()
        decision_metadata = await _extract_submit_decision_metadata(raw_request)

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

        result = await service.submit_order(
            order_request,
            decision_metadata=decision_metadata,
        )
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
        source_labels = broker_sources_from_mode(meta)
        return OrderResultSchema(
            broker_order_id=result.broker_order_id,
            status=result.status,
            filled_price=float(result.filled_price) if result.filled_price else None,
            filled_quantity=float(result.filled_quantity) if result.filled_quantity else None,
            error_message=result.error_message,
            broker_mode=BrokerModeSchema(**meta),
            **source_labels,
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
async def dry_run_order(request: OrderDryRunRequestSchema, raw_request: Request):
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
        decision_metadata = await _extract_submit_decision_metadata(raw_request)

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

        result = service.dry_run_order(
            order_request,
            portfolio_context=portfolio_context,
            persist_decision=True,
            decision_source="dry_run",
            intent="manual",
            decision_metadata=decision_metadata,
        )
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

        meta = get_broker_mode_metadata()
        return OrderDryRunResultSchema(
            status=result["status"],
            mode_guard_ok=result["mode_guard_ok"],
            request_valid=result["request_valid"],
            estimated_notional=result["estimated_notional"],
            issues=[OrderDryRunIssueSchema(**issue) for issue in result["issues"]],
            warnings=[OrderDryRunIssueSchema(**warning) for warning in result.get("warnings", [])],
            preflight_decision=OrderDryRunPreflightDecisionSchema(**result["preflight_decision"]),
            preflight_context=preflight_context_schema,
            broker_mode=BrokerModeSchema(**meta),
            **_dry_run_source_meta(meta),
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
