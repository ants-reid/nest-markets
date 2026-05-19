"""Execution mode routing service for approved deterministic risk decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import ExecutionMode

ExecutionModeType = Literal["paper", "confirm_live", "auto_live"]
ResolvedExecutionMode = Literal["paper", "confirm_live", "auto_live", "blocked"]

MODE_PAPER: str = "paper"
MODE_PENDING_APPROVAL: str = "pending_approval"


@dataclass(frozen=True)
class ExecutionModeDecision:
    """Result of deterministic execution mode routing (legacy path)."""

    proceed_to_execution: bool
    selected_execution_mode: ResolvedExecutionMode


@dataclass(frozen=True)
class ExecutionRoute:
    """Resolved execution routing details."""

    mode: str
    requires_approval: bool
    allows_live_orders: bool
    execution_mode_id: UUID


class ExecutionModeService:
    """Selects execution routing mode from the active DB record."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def get_route(self) -> ExecutionRoute:
        """Query the active execution mode and resolve routing policy.

        Raises:
            ValueError: If no active execution mode record exists.
        """
        if self._session is None:
            raise RuntimeError("Session required for get_route")
        mode: ExecutionMode | None = (
            self._session.query(ExecutionMode)
            .filter(ExecutionMode.is_active == True)  # noqa: E712
            .first()
        )
        if mode is None:
            raise ValueError("No active execution mode found")

        resolved_mode: str = mode.name
        # Live orders are always blocked in MVP; downgrade "live" to paper
        if resolved_mode == "live":
            resolved_mode = MODE_PAPER

        # auto_paper requires no user approval (AI-initiated paper trades)
        requires_approval = (
            False
            if resolved_mode == "auto_paper"
            else getattr(mode, "requires_approval", "inactive") == "active"
        )

        return ExecutionRoute(
            mode=resolved_mode,
            requires_approval=requires_approval,
            allows_live_orders=False,
            execution_mode_id=mode.id,
        )

    def is_live_enabled(self) -> bool:
        """Live execution is always disabled in MVP."""
        return False

    # ------------------------------------------------------------------ #
    # Legacy path — kept for backward compatibility                       #
    # ------------------------------------------------------------------ #
    def route(
        self, approved: bool, requested_mode: ExecutionModeType
    ) -> ExecutionModeDecision:
        """Resolve execution mode from approval state and requested routing mode."""
        if not approved:
            return ExecutionModeDecision(
                proceed_to_execution=False,
                selected_execution_mode="blocked",
            )

        return ExecutionModeDecision(
            proceed_to_execution=True,
            selected_execution_mode=requested_mode,
        )
