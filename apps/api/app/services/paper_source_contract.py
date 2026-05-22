"""Canonical broker/paper source contract helpers.

This module centralizes the additive source labels exposed by API responses so
simulator paper and IBKR paper cannot drift into ambiguous wording.
"""

from __future__ import annotations

from typing import Any

SOURCE_INTERNAL_MOCK_SIMULATOR = "internal_mock_simulator"
SOURCE_IBKR_PAPER = "ibkr_paper"
SOURCE_IBKR_LIVE_LOCKED = "ibkr_live_locked"
SOURCE_BROKER_DRY_RUN = "broker_dry_run"

CANONICAL_PAPER_ROUTE = "/broker/orders"

SERIOUS_PAPER_SOURCE = SOURCE_IBKR_PAPER


def canonical_paper_metadata(*, is_canonical_paper: bool, broker_account_mode: str) -> dict[str, Any]:
    """Return additive metadata describing the operational serious-paper contract."""
    return {
        "serious_paper_source": SERIOUS_PAPER_SOURCE,
        "is_canonical_paper": is_canonical_paper,
        "canonical_paper_route": CANONICAL_PAPER_ROUTE,
        "broker_account_mode": broker_account_mode,
        "live_state": SOURCE_IBKR_LIVE_LOCKED,
    }


def simulator_execution_sources() -> dict[str, Any]:
    """Return source labels for internal simulator execution routes."""
    return {
        "execution_source": SOURCE_INTERNAL_MOCK_SIMULATOR,
        "balance_source": "app_simulated",
        "fees_source": "estimated",
        "fills_source": "simulated",
        "positions_source": "app_db_simulated",
        **canonical_paper_metadata(is_canonical_paper=False, broker_account_mode="simulator"),
        "paper_path_note": (
            "Internal simulator path only. Use IBKR paper broker routes for serious paper validation."
        ),
        "simulator_warning": "Internal simulator only. This is not the canonical IBKR paper proving path.",
    }


def live_locked_execution_sources() -> dict[str, Any]:
    """Return source labels for live-locked scaffolding responses."""
    return {
        "execution_source": SOURCE_IBKR_LIVE_LOCKED,
        "balance_source": SOURCE_IBKR_LIVE_LOCKED,
        "fees_source": "unavailable",
        "fills_source": "unavailable",
        "positions_source": SOURCE_IBKR_LIVE_LOCKED,
        **canonical_paper_metadata(is_canonical_paper=False, broker_account_mode="live"),
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
            **canonical_paper_metadata(is_canonical_paper=False, broker_account_mode="live"),
            "paper_path_note": "Live mode configured but live submit remains locked.",
        }

    return {
        "execution_source": SOURCE_IBKR_PAPER,
        "balance_source": SOURCE_IBKR_PAPER,
        "fees_source": "ibkr_reported",
        "fills_source": SOURCE_IBKR_PAPER,
        "positions_source": SOURCE_IBKR_PAPER,
        **canonical_paper_metadata(is_canonical_paper=True, broker_account_mode="paper"),
        "paper_path_note": "IBKR paper is the canonical serious paper trading path.",
    }


def broker_dry_run_sources(meta: dict[str, object]) -> dict[str, Any]:
    """Return dry-run route source labels without implying a submit already occurred."""
    mode = str(meta.get("mode") or "paper").lower()
    if mode == "live":
        return {
            "execution_source": SOURCE_BROKER_DRY_RUN,
            "balance_source": SOURCE_IBKR_LIVE_LOCKED,
            "fees_source": "unavailable",
            "fills_source": "pending_broker_fill",
            "positions_source": SOURCE_IBKR_LIVE_LOCKED,
            **canonical_paper_metadata(is_canonical_paper=False, broker_account_mode="live"),
            "paper_path_note": "Dry-run stays available for contract inspection, but live submit remains locked.",
        }

    return {
        "execution_source": SOURCE_BROKER_DRY_RUN,
        "balance_source": SOURCE_IBKR_PAPER,
        "fees_source": "pending_broker_report",
        "fills_source": "pending_broker_fill",
        "positions_source": SOURCE_IBKR_PAPER,
        **canonical_paper_metadata(is_canonical_paper=True, broker_account_mode="paper"),
        "paper_path_note": "Dry-run validates the canonical IBKR paper submit path without placing an order.",
    }
