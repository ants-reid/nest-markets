"""MH-145-A drift-lock proof.

The MH-145-A scaffolding ships ``MarketContextSnapshotService`` but does
NOT wire it into ``auto_paper_trader_worker.py``. This test programmatically
proves that wiring has not happened, by asserting:

1. The worker source still constructs ``RiskInput`` with the hardcoded
   placeholders ``spread_bps=0.0``, ``daily_drawdown_pct=0.0``,
   ``recent_losses_count=0`` and ``last_loss_at=None``.
2. The worker module does NOT import the new
   ``MarketContextSnapshotService`` symbol.

If MH-145-B (the wiring phase) lands, this test must be updated AT THE
SAME TIME — failure to update is the intended drift-lock signal.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import app.workers.auto_paper_trader_worker as worker_module


WORKER_SOURCE_PATH = Path(worker_module.__file__)


def _read_worker_source() -> str:
    return WORKER_SOURCE_PATH.read_text(encoding="utf-8")


def test_worker_still_uses_placeholder_risk_inputs():
    """The worker must still pass placeholder zeros into ``RiskInput``."""
    src = _read_worker_source()
    # Each placeholder line must be present verbatim. We assert presence
    # rather than absence to keep the test resilient to whitespace edits.
    assert "spread_bps=0.0" in src, (
        "auto_paper_trader_worker no longer hardcodes spread_bps=0.0 — "
        "wiring may have started; update MH-145-B ledger entry first."
    )
    assert "daily_drawdown_pct=0.0" in src, (
        "auto_paper_trader_worker no longer hardcodes daily_drawdown_pct=0.0 "
        "— wiring may have started; update MH-145-B ledger entry first."
    )
    assert "recent_losses_count=0" in src, (
        "auto_paper_trader_worker no longer hardcodes recent_losses_count=0 "
        "— wiring may have started; update MH-145-B ledger entry first."
    )
    assert "last_loss_at=None" in src, (
        "auto_paper_trader_worker no longer hardcodes last_loss_at=None — "
        "wiring may have started; update MH-145-B ledger entry first."
    )


def test_worker_does_not_import_market_context_snapshot_service():
    """The worker must NOT import ``MarketContextSnapshotService`` yet."""
    src = _read_worker_source()
    assert "MarketContextSnapshotService" not in src, (
        "auto_paper_trader_worker imports MarketContextSnapshotService — "
        "MH-145-A is scaffolding ONLY; wiring belongs to MH-145-B."
    )
    assert "market_context_snapshot_service" not in src, (
        "auto_paper_trader_worker imports the snapshot module — "
        "MH-145-A is scaffolding ONLY; wiring belongs to MH-145-B."
    )


def test_market_context_snapshot_service_module_importable():
    """The MH-145-A scaffolding module must import cleanly."""
    mod = importlib.import_module(
        "app.services.market_context_snapshot_service"
    )
    assert hasattr(mod, "MarketContextSnapshotService")
    assert hasattr(mod, "MarketContextSnapshot")
