"""MH-FEED-MONITOR-001 — Read-only feed monitor aggregator."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from app.config import get_settings
from app.schemas.feed_monitor import (
    FeedMonitorResponseSchema,
    FeedMonitorRowSchema,
    FeedMonitorSummarySchema,
)
from app.services.broker_mode_guard import (
    BrokerModeInconsistencyError,
    check_ibkr_gateway,
    get_broker_mode_metadata,
    is_live_mode_enabled,
    is_paper_account_id,
)
from app.services.provider_inventory_service import list_provider_inventory
from app.services.trading_control_service import TradingControlMisconfiguredError
from app.services.trading_control_service import assert_mode_configuration_consistent

_CATEGORY_ORDER = {"feeds_in": 0, "feeds_out": 1, "runtime": 2}
_STATUS_ORDER = {"error": 0, "down": 1, "degraded": 2, "unknown": 3, "ok": 4}


def _row_action(*, name: str, configured: bool | None, status: str, category: str) -> str:
    if configured is False:
        if name == "feeds_in.polygon_provider":
            return "Configure POLYGON_API_KEY to restore upstream market-data coverage."
        if name.startswith("feeds_in.ibkr"):
            return "Set IBKR gateway URL so market-data gateway checks can resolve."
        if name.startswith("feeds_out.openai"):
            return "Configure OPENAI_API_KEY before enabling any LLM-backed outbound path."
        if name.startswith("feeds_out.ibkr"):
            return "Set IBKR gateway URL before relying on broker-facing API flows."
        return f"Configure the required settings for {category.replace('_', ' ')}."
    if status in {"error", "down"}:
        return f"Inspect {name} for runtime failures and review adjacent incidents before changing any controls."
    if status == "degraded":
        return f"Review {name} drift and configuration before trusting this feed in operator workflows."
    return "No immediate action required."


async def _build_broker_runtime_row() -> FeedMonitorRowSchema:
    started = time.perf_counter()
    settings = get_settings()
    gateway_url = (settings.ibkr_gateway_url or "").strip()
    mode_guard_ok = True
    try:
        assert_mode_configuration_consistent()
    except (BrokerModeInconsistencyError, TradingControlMisconfiguredError):
        mode_guard_ok = False

    gateway_reachable = False
    if gateway_url:
        gateway_reachable = await check_ibkr_gateway(gateway_url, timeout=5.0)

    live_enabled = is_live_mode_enabled()
    mode = get_broker_mode_metadata()
    account_id = settings.ibkr_account_id or ""
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    if not mode_guard_ok:
        status = "error"
        detail = "Broker mode configuration is inconsistent; runtime gateway status is advisory only."
    elif gateway_url and gateway_reachable:
        status = "ok"
        detail = "IBKR gateway responded to the lightweight runtime health probe."
    elif gateway_url:
        status = "degraded"
        detail = "IBKR gateway is configured but did not respond to the lightweight runtime health probe."
    else:
        status = "degraded"
        detail = "IBKR gateway URL is not configured; runtime broker feed checks cannot resolve."

    return FeedMonitorRowSchema(
        id="runtime.ibkr_gateway",
        name="runtime.ibkr_gateway",
        category="runtime",
        kind="broker_gateway_runtime",
        status=status,
        configured=bool(gateway_url),
        runtime_reachable=gateway_reachable,
        detail=detail,
        action=(
            "Fix broker mode env alignment before trusting runtime gateway status."
            if not mode_guard_ok
            else _row_action(
                name="runtime.ibkr_gateway",
                configured=bool(gateway_url),
                status=status,
                category="runtime",
            )
        ),
        checked_at=datetime.now(UTC).isoformat(),
        latency_ms=latency_ms,
        target=gateway_url or None,
        tags=[mode.get("mode", "unknown"), "broker", "runtime"],
        extra={
            "mode_guard_ok": mode_guard_ok,
            "broker_mode": mode,
            "account_id": account_id,
            "account_is_paper": is_paper_account_id(account_id),
            "live_execution_enabled": live_enabled,
        },
    )


def _provider_row_to_feed_row(row) -> FeedMonitorRowSchema:
    target = row.extra.get("url") if isinstance(row.extra, dict) else None
    return FeedMonitorRowSchema(
        id=row.name,
        name=row.name,
        category=row.category,
        kind="provider_probe",
        status=row.status,
        configured=row.configured,
        runtime_reachable=None,
        detail=row.detail,
        action=_row_action(
            name=row.name,
            configured=row.configured,
            status=row.status,
            category=row.category,
        ),
        checked_at=row.checked_at,
        latency_ms=row.latency_ms,
        target=target if isinstance(target, str) and target else None,
        tags=[row.category, "probe"],
        extra=dict(row.extra),
    )


def _overall(rows: list[FeedMonitorRowSchema]) -> str:
    statuses = {row.status for row in rows}
    if not rows:
        return "unknown"
    if statuses == {"ok"}:
        return "ok"
    if "down" in statuses or "error" in statuses:
        return "down"
    if "degraded" in statuses:
        return "degraded"
    return "unknown"


def _build_summary(rows: list[FeedMonitorRowSchema]) -> FeedMonitorSummarySchema:
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    configured = 0
    runtime_reachable = 0
    issue_count = 0
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        by_category[row.category] = by_category.get(row.category, 0) + 1
        if row.configured:
            configured += 1
        if row.runtime_reachable:
            runtime_reachable += 1
        if row.status != "ok":
            issue_count += 1
    return FeedMonitorSummarySchema(
        total=len(rows),
        configured=configured,
        runtime_reachable=runtime_reachable,
        issue_count=issue_count,
        by_status=by_status,
        by_category=by_category,
    )


def _next_actions(rows: list[FeedMonitorRowSchema]) -> list[str]:
    actions: list[str] = []
    for row in rows:
        if row.status == "ok" or not row.action:
            continue
        if row.action not in actions:
            actions.append(row.action)
    return actions[:6]


async def get_feed_monitor_snapshot() -> FeedMonitorResponseSchema:
    provider_rows = [
        _provider_row_to_feed_row(row)
        for row in list_provider_inventory()
        if row.category in {"feeds_in", "feeds_out"}
    ]
    runtime_row = await _build_broker_runtime_row()
    rows = provider_rows + [runtime_row]
    rows.sort(
        key=lambda row: (
            _CATEGORY_ORDER.get(row.category, 99),
            _STATUS_ORDER.get(row.status, 99),
            row.name,
        )
    )
    overall = _overall(rows)
    summary = _build_summary(rows)
    return FeedMonitorResponseSchema(
        overall=overall,
        advisory=(
            "Read-only feed posture over registered provider probes plus broker gateway runtime reachability. "
            "No control surfaces are exposed here; auto-paper, auto trading, and live trading remain OFF."
        ),
        as_of_utc=datetime.now(UTC).isoformat(),
        summary=summary,
        next_actions=_next_actions(rows),
        rows=rows,
    )
