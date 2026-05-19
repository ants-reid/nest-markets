"""MH-MON-07 — Provider Inventory derivation.

Pure read-only helper that converts a ``health_registry.snapshot()`` into a
flat provider-configuration view. Categorises rows by name prefix:

* ``feeds_in.*``  -> ``"feeds_in"``
* ``feeds_out.*`` -> ``"feeds_out"``
* anything else   -> ``"infrastructure"``

The ``configured`` boolean comes from the probe's ``extra['configured']``
field when present; otherwise it falls back to ``status == 'ok'``. No
secrets are emitted — feeds-in / feeds-out probes are documented as
config-presence-only and never include the API key value itself.

Drift-lock guarantee: this module performs no writes, calls no broker
submission path, and does not bypass ``trading_control_service``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional

from app.services.health_registry import ServiceHealth, snapshot

ProviderCategory = Literal["feeds_in", "feeds_out", "infrastructure"]

# Keys that must NEVER be echoed even if a probe accidentally includes them.
_SECRET_KEY_FRAGMENTS = ("api_key", "secret", "token", "password")


@dataclass(frozen=True)
class ProviderInventoryRow:
    name: str
    category: ProviderCategory
    status: str
    configured: bool
    detail: Optional[str]
    latency_ms: Optional[float]
    checked_at: str
    extra: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _classify(name: str) -> ProviderCategory:
    if name.startswith("feeds_in."):
        return "feeds_in"
    if name.startswith("feeds_out."):
        return "feeds_out"
    return "infrastructure"


def _scrub(extra: Dict[str, Any]) -> Dict[str, Any]:
    """Drop any keys whose name suggests a secret value."""
    if not extra:
        return {}
    cleaned: Dict[str, Any] = {}
    for key, value in extra.items():
        lowered = str(key).lower()
        if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
            continue
        cleaned[key] = value
    return cleaned


def _row_from_health(item: ServiceHealth) -> ProviderInventoryRow:
    extra = _scrub(dict(item.extra or {}))
    if "configured" in extra:
        configured = bool(extra["configured"])
    else:
        configured = item.status == "ok"
    return ProviderInventoryRow(
        name=item.name,
        category=_classify(item.name),
        status=item.status,
        configured=configured,
        detail=item.detail,
        latency_ms=item.latency_ms,
        checked_at=item.checked_at,
        extra=extra,
    )


def list_provider_inventory() -> List[ProviderInventoryRow]:
    """Return the flat provider-inventory view derived from current probes."""
    return [_row_from_health(item) for item in snapshot()]


def provider_inventory_response() -> Dict[str, Any]:
    """Endpoint-shaped payload: rows + aggregate counts per category."""
    rows = list_provider_inventory()
    by_category: Dict[str, int] = {}
    configured_by_category: Dict[str, int] = {}
    for row in rows:
        by_category[row.category] = by_category.get(row.category, 0) + 1
        if row.configured:
            configured_by_category[row.category] = (
                configured_by_category.get(row.category, 0) + 1
            )
    return {
        "providers": [row.to_dict() for row in rows],
        "totals": {
            "count": len(rows),
            "by_category": by_category,
            "configured_by_category": configured_by_category,
        },
    }
