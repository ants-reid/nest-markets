"""MH-MON-01 — Health endpoint registry.

Read-only aggregator that lists known service probes and their last-known
status. This phase ships the *registry contract* and a single built-in probe
(``database``). Future phases (MH-MON-02 / MH-MON-03 / MH-MON-04) plug in
feeds-in / feeds-out / safety-decision probes.

Contract:
- A *probe* is a zero-argument callable that returns a ``ProbeResult``.
- Registration is module-global and additive; nothing is removed at runtime.
- The endpoint never enables, disables, or mutates any service. It only reads.
- Probes that raise are caught and reported as ``status='error'``.

Drift-lock guarantee: this module performs no writes to any trading table,
holds no locks, and never calls ``BrokerService.submit_auto_order`` or
``assert_auto_trading_allowed``.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Literal, Optional

ProbeStatus = Literal["ok", "degraded", "down", "unknown", "error"]


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of a single probe call."""

    status: ProbeStatus
    detail: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceHealth:
    """Snapshot row for one registered service."""

    name: str
    status: ProbeStatus
    detail: Optional[str]
    latency_ms: Optional[float]
    checked_at: str
    extra: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


ProbeFn = Callable[[], ProbeResult]


_REGISTRY: Dict[str, ProbeFn] = {}


def register_probe(name: str, probe: ProbeFn) -> None:
    """Register or replace a probe under ``name``. Idempotent."""
    if not name or not isinstance(name, str):
        raise ValueError("probe name must be a non-empty string")
    if not callable(probe):
        raise TypeError("probe must be callable")
    _REGISTRY[name] = probe


def unregister_probe(name: str) -> None:
    """Remove a probe; no-op if not registered. Test-only convenience."""
    _REGISTRY.pop(name, None)


def list_registered() -> List[str]:
    """Return the names of all currently registered probes."""
    return sorted(_REGISTRY.keys())


def run_registered(name: str) -> ServiceHealth:
    """Run exactly one registered probe by name.

    Raises
    ------
    KeyError
        If ``name`` is not a registered probe id.
    """
    if name not in _REGISTRY:
        raise KeyError(name)
    return _run_one(name, _REGISTRY[name])


def _run_one(name: str, probe: ProbeFn) -> ServiceHealth:
    start = time.perf_counter()
    try:
        result = probe()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        if not isinstance(result, ProbeResult):
            return ServiceHealth(
                name=name,
                status="error",
                detail=f"probe returned {type(result).__name__}, expected ProbeResult",
                latency_ms=latency_ms,
                checked_at=datetime.now(UTC).isoformat(),
                extra={},
            )
        return ServiceHealth(
            name=name,
            status=result.status,
            detail=result.detail,
            latency_ms=latency_ms,
            checked_at=datetime.now(UTC).isoformat(),
            extra=dict(result.extra),
        )
    except Exception as exc:  # noqa: BLE001 — probes must never crash the endpoint
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return ServiceHealth(
            name=name,
            status="error",
            detail=f"{type(exc).__name__}: {exc}",
            latency_ms=latency_ms,
            checked_at=datetime.now(UTC).isoformat(),
            extra={},
        )


def snapshot() -> List[ServiceHealth]:
    """Run every registered probe once and return the results, sorted by name."""
    return [_run_one(name, _REGISTRY[name]) for name in sorted(_REGISTRY.keys())]


# ---------------------------------------------------------------------------
# Built-in probes
# ---------------------------------------------------------------------------


def _database_probe() -> ProbeResult:
    """Cheap ``SELECT 1`` against the configured database."""
    from sqlalchemy import text

    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        return ProbeResult(status="ok", detail="select 1 ok")
    finally:
        session.close()


def register_default_probes() -> None:
    """Register the built-in probes. Safe to call multiple times.

    Includes:
    - ``database`` (this module)
    - ``feeds_in.*`` (MH-MON-02 — registered via ``feeds_in_probe``)
    - ``feeds_out.*`` (MH-MON-03 — registered via ``feeds_out_probe``)
    """
    register_probe("database", _database_probe)
    # Imported lazily to avoid a circular dependency at module-load time
    # (the probe modules import from this module).
    from app.services.feeds_in_probe import register_feeds_in_probes
    from app.services.feeds_out_probe import register_feeds_out_probes

    register_feeds_in_probes()
    register_feeds_out_probes()


# Register defaults at import time so the endpoint always has at least one row.
register_default_probes()
