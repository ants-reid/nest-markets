"""MH-MON-02 — Feeds-In probes.

Read-only configuration probes for the data-feeds the system *consumes*
(market-data providers, broker market-data gateway). These are intentionally
config-presence checks only — they never open sockets, never make HTTP calls,
and never authenticate against external APIs. That keeps the
``/health/services`` endpoint cheap, deterministic, and side-effect-free.

Live network reachability probes can be added later by appending more
registrations; they should be opt-in (env-gated) so the default endpoint
stays cheap.

Drift-lock guarantee: this module performs no writes, calls no broker
submission path, and does not touch ``trading_control_service``.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.health_registry import ProbeResult, register_probe


def _polygon_provider_probe() -> ProbeResult:
    settings = get_settings()
    key = (getattr(settings, "polygon_api_key", "") or "").strip()
    if key:
        return ProbeResult(
            status="ok",
            detail="POLYGON_API_KEY configured",
            extra={"configured": True},
        )
    return ProbeResult(
        status="degraded",
        detail="POLYGON_API_KEY not configured (provider returns empty bars)",
        extra={"configured": False},
    )


def _ibkr_market_data_gateway_probe() -> ProbeResult:
    """Configuration-presence check for the IBKR market-data gateway URL.

    Does NOT contact the gateway. A live reachability check exists in
    ``broker_mode_guard.check_ibkr_gateway`` but is async and side-effecting;
    we keep this probe purely synchronous and config-level.
    """
    settings = get_settings()
    url = (getattr(settings, "ibkr_gateway_url", "") or "").strip()
    if url:
        return ProbeResult(
            status="ok",
            detail=f"ibkr_gateway_url configured: {url}",
            extra={"configured": True, "url": url},
        )
    return ProbeResult(
        status="degraded",
        detail="ibkr_gateway_url not configured",
        extra={"configured": False},
    )


# Stable probe names (used by tests and by future MH-MON-04 aggregator).
POLYGON_PROBE_NAME = "feeds_in.polygon_provider"
IBKR_MARKET_DATA_PROBE_NAME = "feeds_in.ibkr_market_data_gateway"


def register_feeds_in_probes() -> None:
    """Register all feeds-in probes. Safe to call multiple times (idempotent)."""
    register_probe(POLYGON_PROBE_NAME, _polygon_provider_probe)
    register_probe(IBKR_MARKET_DATA_PROBE_NAME, _ibkr_market_data_gateway_probe)
