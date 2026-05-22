"""Canonical broker/paper source contract helpers.

This module centralizes the additive source labels exposed by API responses so
simulator paper and IBKR paper cannot drift into ambiguous wording.
"""

from __future__ import annotations

from typing import Any

SOURCE_INTERNAL_MOCK_SIMULATOR = "internal_mock_simulator"
SOURCE_IBKR_PAPER = "ibkr_paper"
SOURCE_IBKR_LIVE_LOCKED = "ibkr_live_locked"

SERIOUS_PAPER_SOURCE = SOURCE_IBKR_PAPER


def simulator_execution_sources() -> dict[str, Any]:
    """Return source labels for internal simulator execution routes."""
    return {
        "execution_source": SOURCE_INTERNAL_MOCK_SIMULATOR,
        "balance_source": "app_simulated",
        "fees_source": "estimated",
        "fills_source": "simulated",
        "positions_source": "app_db_simulated",
        "serious_paper_source": SERIOUS_PAPER_SOURCE,
        "is_canonical_paper": False,
        "paper_path_note": (
            "Internal simulator path only. Use IBKR paper broker routes for serious paper validation."
        ),
    }


def live_locked_execution_sources() -> dict[str, Any]:
    """Return source labels for live-locked scaffolding responses."""
    return {
        "execution_source": SOURCE_IBKR_LIVE_LOCKED,
        "balance_source": SOURCE_IBKR_LIVE_LOCKED,
        "fees_source": "unavailable",
        "fills_source": "unavailable",
        "positions_source": SOURCE_IBKR_LIVE_LOCKED,
        "serious_paper_source": SERIOUS_PAPER_SOURCE,
        "is_canonical_paper": False,
        "paper_path_note": "Live trading remains locked in this phase.",
    }


def broker_sources_from_mode(meta: dict[str, object]) -> dict[str, Any]:
    """Return broker route source labels from current broker mode metadata."""
    mode = str(meta.get("mode") or "paper").lower()
    if mode == "live":
        return {
            "execution_source": SOURCE_IBKR_LIVE_LOCKED,
            "balance_source": SOURCE_IBKR_LIVE_LOCKED,
            "fees_source": "unavailable",
            "fills_source": "unavailable",
            "positions_source": SOURCE_IBKR_LIVE_LOCKED,
            "serious_paper_source": SERIOUS_PAPER_SOURCE,
            "is_canonical_paper": False,
            "paper_path_note": "Live mode configured but live submit remains locked.",
        }

    return {
        "execution_source": SOURCE_IBKR_PAPER,
        "balance_source": SOURCE_IBKR_PAPER,
        "fees_source": "ibkr_reported",
        "fills_source": SOURCE_IBKR_PAPER,
        "positions_source": SOURCE_IBKR_PAPER,
        "serious_paper_source": SERIOUS_PAPER_SOURCE,
        "is_canonical_paper": True,
        "paper_path_note": "IBKR paper is the canonical serious paper trading path.",
    }
