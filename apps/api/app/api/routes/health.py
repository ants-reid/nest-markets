from fastapi import APIRouter

from app.services.health_registry import list_registered, snapshot
from app.services.provider_inventory_service import provider_inventory_response
from app.services.trading_safety_aggregator import evaluate_trading_safety

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, str]:
    """Return a simple health response."""
    return {"status": "ok"}


@router.get("/services")
def health_services() -> dict[str, object]:
    """MH-MON-01 — Read-only aggregate of every registered service probe.

    This endpoint never enables, disables, or mutates any service. Probes that
    fail are reported with ``status='error'`` and never crash the response.
    """
    rows = [s.to_dict() for s in snapshot()]
    statuses = {r["status"] for r in rows}
    if not rows:
        overall = "unknown"
    elif statuses == {"ok"}:
        overall = "ok"
    elif "down" in statuses or "error" in statuses:
        overall = "down"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "unknown"
    return {
        "overall": overall,
        "registered": list_registered(),
        "services": rows,
    }


@router.get("/safety")
def health_safety() -> dict:
    """MH-MON-04 — Read-only Trading Safety Decision aggregator.

    Combines health probes, trading halt state, and trading-control state into
    a single advisory verdict. The endpoint never enables, disables, or
    modifies any trading control. ``safe_to_enable_enforcement=True`` is a
    *recommendation* only; the actual enforcement gates remain in their owning
    modules (``trading_control_service``, ``broker_mode_guard``).
    """
    return evaluate_trading_safety().to_dict()


@router.get("/providers")
def health_providers() -> dict:
    """MH-MON-07 — Read-only Provider Configuration inventory.

    Flat view of every registered probe classified by category (feeds_in /
    feeds_out / infrastructure) with a ``configured`` boolean derived from
    the probe's existing ``extra`` payload. Secrets are never echoed: keys
    matching ``api_key|secret|token|password`` are stripped before serialising.

    This endpoint never enables, disables, or modifies any provider. It is a
    pure derivation of ``snapshot()``; no new probes are run.
    """
    return provider_inventory_response()
