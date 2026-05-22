"""Read-only serious-paper routing contract for operational workflows.

This service answers one question only: whether an operator-facing
"serious paper" workflow may route toward the canonical IBKR paper submit
path. It never submits an order and never weakens broker/trading-control
guards.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.broker_mode_guard import get_broker_mode_metadata
from app.services.paper_source_contract import (
    CANONICAL_PAPER_ROUTE,
    SERIOUS_PAPER_SOURCE,
    SOURCE_IBKR_LIVE_LOCKED,
    SOURCE_IBKR_PAPER,
)

SERIOUS_PAPER_REQUESTED_MODE = "serious_paper"
SIMULATOR_PAPER_ROUTE = "/execution/paper"


@dataclass(frozen=True)
class SeriousPaperRoutingDecision:
    """Resolved routing metadata for operational serious-paper workflows."""

    requested_mode: str
    resolved_execution_source: str | None
    resolved_route: str | None
    simulator_route: str
    simulator_allowed_for_serious_paper: bool
    broker_account_mode_required: str
    current_broker_account_mode: str
    can_route_to_broker_paper: bool
    blocked_reason: str | None
    live_state: str
    would_block: bool
    is_submit: bool
    next_required_action: str
    serious_paper_source: str
    canonical_paper_route: str
    broker_mode: dict[str, object]


class SeriousPaperRoutingService:
    """Resolve the safe operational route for serious-paper workflows."""

    def resolve_route(self) -> SeriousPaperRoutingDecision:
        """Return the route decision for intentional serious-paper workflows.

        Serious paper is allowed to resolve only to the canonical broker paper
        path, and only when the broker env tuple is coherently paper.
        """
        meta = get_broker_mode_metadata()
        coherent_paper = bool(meta.get("paper_trading_enabled"))
        coherent_live = (
            str(meta.get("mode") or "").lower() == "live"
            and bool(meta.get("live_execution_enabled"))
        )

        if coherent_paper:
            return SeriousPaperRoutingDecision(
                requested_mode=SERIOUS_PAPER_REQUESTED_MODE,
                resolved_execution_source=SOURCE_IBKR_PAPER,
                resolved_route=CANONICAL_PAPER_ROUTE,
                simulator_route=SIMULATOR_PAPER_ROUTE,
                simulator_allowed_for_serious_paper=False,
                broker_account_mode_required="paper",
                current_broker_account_mode="paper",
                can_route_to_broker_paper=True,
                blocked_reason=None,
                live_state=SOURCE_IBKR_LIVE_LOCKED,
                would_block=False,
                is_submit=False,
                next_required_action=(
                    "Run POST /broker/orders/dry-run for the intended order, then submit through "
                    "POST /broker/orders only if the paper preflight remains acceptable."
                ),
                serious_paper_source=SERIOUS_PAPER_SOURCE,
                canonical_paper_route=CANONICAL_PAPER_ROUTE,
                broker_mode=meta,
            )

        if coherent_live:
            blocked_reason = (
                "Serious paper routing is blocked because broker mode is coherently live and "
                "live submit remains locked."
            )
        else:
            blocked_reason = (
                "Serious paper routing is blocked because broker mode is not coherently paper."
            )

        return SeriousPaperRoutingDecision(
            requested_mode=SERIOUS_PAPER_REQUESTED_MODE,
            resolved_execution_source=None,
            resolved_route=None,
            simulator_route=SIMULATOR_PAPER_ROUTE,
            simulator_allowed_for_serious_paper=False,
            broker_account_mode_required="paper",
            current_broker_account_mode="live" if coherent_live else "unknown",
            can_route_to_broker_paper=False,
            blocked_reason=blocked_reason,
            live_state=SOURCE_IBKR_LIVE_LOCKED,
            would_block=True,
            is_submit=False,
            next_required_action=(
                "Restore a coherent paper broker/account mode before using the canonical serious-paper path."
            ),
            serious_paper_source=SERIOUS_PAPER_SOURCE,
            canonical_paper_route=CANONICAL_PAPER_ROUTE,
            broker_mode=meta,
        )