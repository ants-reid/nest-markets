"""MH-MON-04 — Trading Safety Decision aggregator.

Pure read-only aggregator that combines three independent safety signals into
a single ``TradingSafetyDecision``:

1. **Health probes** (MH-MON-01 / MH-MON-02 / MH-MON-03) — `/health/services`
2. **Trading halt** state (MH-39) — ``TradingHaltService.is_halt_active``
3. **Trading control** state (MH-36B) — ``trading_control_service.get_trading_mode``

The decision is **read-only**. It NEVER:
- enables auto-paper enforcement
- enables auto trading
- enables live trading
- modifies any database row
- calls ``BrokerService.submit_auto_order``
- bypasses ``trading_control_service`` gates
- weakens ``assert_auto_trading_allowed``

It is consumed by future UI surfaces (MH-MON-06) and by audits, but it is
**advisory** — the actual gates remain in their owning modules.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.services.health_registry import ServiceHealth, snapshot

# Probe names that count as "core" safety dependencies. If any of these are
# down/error, the system is not safe to enable enforcement.
CORE_PROBE_NAMES = (
    "database",
    "feeds_in.polygon_provider",
    "feeds_in.ibkr_market_data_gateway",
    "feeds_out.openai_provider",
    "feeds_out.ibkr_order_gateway",
)


@dataclass(frozen=True)
class TradingSafetyDecision:
    """Aggregate read-only safety verdict at a point in time."""

    safe_to_enable_enforcement: bool
    overall_health: str  # ok | degraded | down | unknown
    halt_active: bool
    halt_reason: Optional[str]
    trading_mode: str
    execution_control: str
    arming_state: str
    auto_trading_allowed: bool
    blocking_reasons: List[str] = field(default_factory=list)
    advisory_reasons: List[str] = field(default_factory=list)
    health_summary: Dict[str, str] = field(default_factory=dict)
    checked_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _summarize_health(rows: List[ServiceHealth]) -> tuple[str, Dict[str, str]]:
    summary = {row.name: row.status for row in rows}
    statuses = set(summary.values())
    if not statuses:
        return "unknown", summary
    if statuses == {"ok"}:
        return "ok", summary
    if "down" in statuses or "error" in statuses:
        return "down", summary
    if "degraded" in statuses:
        return "degraded", summary
    return "unknown", summary


def evaluate_trading_safety() -> TradingSafetyDecision:
    """Compute the current ``TradingSafetyDecision`` from live sources.

    Imports are local to this function to (a) keep import cost zero for callers
    that never invoke it, and (b) avoid circular imports with the FastAPI
    routing layer.
    """
    # --- Health probes ---
    rows = snapshot()
    overall_health, health_summary = _summarize_health(rows)

    # --- Trading halt ---
    halt_active = False
    halt_reason: Optional[str] = None
    try:
        from app.db.session import SessionLocal
        from app.services.trading_halt_service import TradingHaltService

        session = SessionLocal()
        try:
            halt_service = TradingHaltService(session)
            status = halt_service.get_status(scope="global")
            halt_active = bool(getattr(status, "emergency_stop_active", False))
            halt_reason = getattr(status, "blocked_reason", None)
        finally:
            session.close()
    except Exception as exc:  # noqa: BLE001 — aggregator must never crash
        # Treat halt-service failure as advisory (we do not have certainty).
        halt_active = False
        halt_reason = f"halt_service_unavailable: {type(exc).__name__}"

    # --- Trading control ---
    trading_mode = "unknown"
    execution_control = "unknown"
    arming_state = "unknown"
    auto_trading_allowed = False
    try:
        from app.services.trading_control_service import get_trading_mode

        state = get_trading_mode()
        trading_mode = getattr(state, "trading_mode", "unknown")
        execution_control = getattr(state, "execution_control", "unknown")
        arming_state = getattr(state, "arming_state", "unknown")
        auto_trading_allowed = bool(getattr(state, "auto_trading_allowed", False))
    except Exception as exc:  # noqa: BLE001
        # If the control service errors, we *cannot* declare it safe.
        trading_mode = "error"
        execution_control = "error"
        arming_state = "error"
        auto_trading_allowed = False
        halt_reason = (halt_reason or "") + f" control_service_error: {type(exc).__name__}"

    # --- Build verdict ---
    blocking: List[str] = []
    advisory: List[str] = []

    if halt_active:
        blocking.append("trading_halt_active")

    if auto_trading_allowed:
        # Drift-lock invariant: this should be False. If it ever flips True
        # while enforcement is supposed to be off, that itself is a blocker.
        blocking.append("auto_trading_allowed_unexpectedly_true")

    # Core probes — any not-ok status is a blocker.
    for name in CORE_PROBE_NAMES:
        status = health_summary.get(name)
        if status is None:
            advisory.append(f"core_probe_missing:{name}")
        elif status in ("down", "error"):
            blocking.append(f"core_probe_unhealthy:{name}:{status}")
        elif status == "degraded":
            advisory.append(f"core_probe_degraded:{name}")

    # Non-core probes that are degraded/down are advisory only.
    for row in rows:
        if row.name in CORE_PROBE_NAMES:
            continue
        if row.status in ("degraded",):
            advisory.append(f"probe_degraded:{row.name}")
        elif row.status in ("down", "error"):
            advisory.append(f"probe_unhealthy:{row.name}:{row.status}")

    safe = (overall_health == "ok") and (not halt_active) and (not blocking)

    return TradingSafetyDecision(
        safe_to_enable_enforcement=safe,
        overall_health=overall_health,
        halt_active=halt_active,
        halt_reason=halt_reason,
        trading_mode=trading_mode,
        execution_control=execution_control,
        arming_state=arming_state,
        auto_trading_allowed=auto_trading_allowed,
        blocking_reasons=blocking,
        advisory_reasons=advisory,
        health_summary=health_summary,
        checked_at=datetime.now(UTC).isoformat(),
    )
