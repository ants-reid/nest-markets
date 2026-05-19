"""MH-MON-03 — Feeds-Out probes.

Read-only configuration probes for the systems the platform *writes to* /
*submits decisions through* (LLM provider, broker order gateway). Like
:mod:`app.services.feeds_in_probe` these are config-presence checks only —
no network I/O, no submissions.

Drift-lock guarantee: this module performs no writes, calls no broker
submission path, does not bypass ``trading_control_service``, and does not
loosen ``BrokerService.submit_auto_order``.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.health_registry import ProbeResult, register_probe


def _openai_provider_probe() -> ProbeResult:
    settings = get_settings()
    key = (getattr(settings, "openai_api_key", "") or "").strip()
    if key:
        return ProbeResult(
            status="ok",
            detail="OPENAI_API_KEY configured",
            extra={"configured": True},
        )
    return ProbeResult(
        status="degraded",
        detail="OPENAI_API_KEY not configured (LLM calls will fail)",
        extra={"configured": False},
    )


def _ibkr_order_gateway_probe() -> ProbeResult:
    """Configuration-presence check for the IBKR order gateway.

    Reports the safety posture of the order path without changing it:
    - ``configured``: gateway URL set
    - ``auto_trading_enabled``: always False (drift lock)
    - ``live_trading_enabled``: always False (drift lock)

    Does NOT call any submission code path.
    """
    settings = get_settings()
    url = (getattr(settings, "ibkr_gateway_url", "") or "").strip()

    extra = {
        "configured": bool(url),
        "url": url or None,
        # The drift-lock state is reported here so MH-MON-04 (Trading Safety
        # Decision aggregator) can read it from a single source. These flags
        # are NOT toggles — they are read-only mirrors of the safety posture.
        "auto_trading_enabled": False,
        "live_trading_enabled": False,
    }
    if url:
        return ProbeResult(
            status="ok",
            detail="ibkr order gateway configured (auto/live trading remain disabled)",
            extra=extra,
        )
    return ProbeResult(
        status="degraded",
        detail="ibkr order gateway not configured",
        extra=extra,
    )


# Stable probe names.
OPENAI_PROBE_NAME = "feeds_out.openai_provider"
IBKR_ORDER_PROBE_NAME = "feeds_out.ibkr_order_gateway"


def register_feeds_out_probes() -> None:
    """Register all feeds-out probes. Idempotent."""
    register_probe(OPENAI_PROBE_NAME, _openai_provider_probe)
    register_probe(IBKR_ORDER_PROBE_NAME, _ibkr_order_gateway_probe)
