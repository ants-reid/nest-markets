"""Drift-lock pin: which modules import the live broker client surface.

Cycle 65 — MH-DRIFTLOCK-BROKER-CLIENT-IMPORT-CATALOG.

Why this pin exists
-------------------
``BrokerGatewayFactory`` and ``IBKRAdapter`` are the seams through
which actual broker traffic flows. Cycle 59 byte-pins the methods
that USE those seams (``BrokerService.submit_auto_order`` etc.), but a
silent new importer of ``BrokerGatewayFactory`` (e.g. a worker that
goes direct to the gateway) would route around the entire submit-gate
chain. This pin freezes the importer set so any new caller is detected.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent / "app"

# Hard subset: ONLY broker_service.py is allowed to import the gateway
# factory. Any other importer would route around the auto-submit gate.
EXPECTED_GATEWAY_FACTORY_IMPORTERS: set[str] = {
    "services/broker_service.py",
}

# Broader catalog: modules that import IBKRAdapter directly. Gate 7 cleanup
# moved broker-facing services onto broker protocols, so the adapter should
# now stay isolated to the broker gateway factory.
EXPECTED_IBKR_ADAPTER_IMPORTERS: set[str] = {
    "clients/broker/gateway_factory.py",
}


def _scan_imports(import_line: str) -> set[str]:
    """Return paths (relative to APP_ROOT) of files that contain the
    given import-line literal. The defining module is excluded so the
    catalog tracks IMPORTERS, not the source of the symbol."""
    out: set[str] = set()
    for p in APP_ROOT.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if import_line in text:
            out.add(p.relative_to(APP_ROOT).as_posix())
    return out


def test_broker_gateway_factory_importers_unchanged() -> None:
    actual = _scan_imports(
        "from app.clients.broker.gateway_factory import BrokerGatewayFactory"
    )
    extra = actual - EXPECTED_GATEWAY_FACTORY_IMPORTERS
    missing = EXPECTED_GATEWAY_FACTORY_IMPORTERS - actual
    msg_parts: list[str] = []
    if extra:
        msg_parts.append(
            "  UNEXPECTED new importer(s) of BrokerGatewayFactory: "
            + ", ".join(sorted(extra))
            + "  -- this routes around BrokerService.submit_auto_order!"
        )
    if missing:
        msg_parts.append(
            "  MISSING expected importer(s): " + ", ".join(sorted(missing))
        )
    assert not msg_parts, (
        "BrokerGatewayFactory import surface drift detected.\n"
        + "\n".join(msg_parts)
        + "\nIf intentional, update EXPECTED_GATEWAY_FACTORY_IMPORTERS "
        "AND ensure the new importer routes through BrokerService."
    )


def test_ibkr_adapter_importers_catalog_exact_match() -> None:
    actual = _scan_imports(
        "from app.clients.broker.ibkr_adapter import IBKRAdapter"
    )
    extra = actual - EXPECTED_IBKR_ADAPTER_IMPORTERS
    missing = EXPECTED_IBKR_ADAPTER_IMPORTERS - actual
    msg_parts: list[str] = []
    if extra:
        msg_parts.append("  Unexpected new importers: " + ", ".join(sorted(extra)))
    if missing:
        msg_parts.append("  Missing expected importers: " + ", ".join(sorted(missing)))
    assert not msg_parts, (
        "IBKRAdapter import catalog drift detected.\n"
        + "\n".join(msg_parts)
        + "\nNew direct importers of IBKRAdapter usually want to go "
        "through BrokerService instead. If the change is intentional, "
        "update EXPECTED_IBKR_ADAPTER_IMPORTERS with a ledger entry."
    )


def test_workers_do_not_import_gateway_factory() -> None:
    """Standalone hard guard: ``app/workers/`` MUST NOT import the
    gateway factory. Workers must route through BrokerService.
    """
    workers_dir = APP_ROOT / "workers"
    offenders: list[str] = []
    for p in workers_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        if "BrokerGatewayFactory" in text:
            offenders.append(p.relative_to(APP_ROOT).as_posix())
    assert not offenders, (
        "A worker now imports BrokerGatewayFactory directly. Workers "
        "MUST route through BrokerService.submit_auto_order so the "
        "trading-control gate runs.\n  " + "\n  ".join(offenders)
    )
