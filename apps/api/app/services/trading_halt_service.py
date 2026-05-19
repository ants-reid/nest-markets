"""Trading halt state and broker enforcement support.

MH-39 introduced halt persistence. MH-79 wires active halt state into broker
preflight and paper submit enforcement while leaving live and auto behavior unchanged.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import TradingHalt
from app.schemas.trading_halt import (
    TradingHaltCreateRequest,
    TradingHaltListResponse,
    TradingHaltResolveRequest,
    TradingHaltResponse,
    TradingHaltStatusResponse,
)


class TradingHaltService:
    """Service for recording and reading future trading halt state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_active_halt(self, scope: str = "global") -> TradingHalt | None:
        normalized_scope = scope.lower()
        return (
            self._session.query(TradingHalt)
            .filter(TradingHalt.scope == normalized_scope, TradingHalt.status == "active")
            .order_by(TradingHalt.triggered_at.desc(), TradingHalt.created_at.desc())
            .first()
        )

    def get_status(self, scope: str = "global") -> TradingHaltStatusResponse:
        active_halt = self.get_active_halt(scope=scope)
        blocked_reason = self.build_blocked_reason(scope=scope)
        return TradingHaltStatusResponse(
            emergency_stop_active=active_halt is not None,
            active_halt=TradingHaltResponse.model_validate(active_halt) if active_halt is not None else None,
            status="active" if active_halt is not None else "clear",
            blocked_reason=blocked_reason,
            enforcement_enabled=True,
            note=(
                "Active halt state is enforced in broker preflight and paper submit paths."
            ),
        )

    def create_halt(self, request: TradingHaltCreateRequest) -> TradingHalt:
        halt = TradingHalt(
            status="active",
            halt_type=request.halt_type,
            scope=request.scope,
            trading_mode=request.trading_mode,
            reason=request.reason,
            triggered_by=request.triggered_by,
            triggered_at=datetime.now(UTC),
            metadata_json=request.metadata_json,
        )
        self._session.add(halt)
        self._session.commit()
        self._session.refresh(halt)
        return halt

    def resolve_halt(self, halt_id, request: TradingHaltResolveRequest) -> TradingHalt | None:
        halt = self._session.get(TradingHalt, halt_id)
        if halt is None:
            return None

        halt.status = "resolved"
        halt.resolved_by = request.resolved_by
        halt.resolution_notes = request.resolution_notes
        halt.resolved_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(halt)
        return halt

    def list_halts(self, limit: int = 50, offset: int = 0, status: str | None = None) -> TradingHaltListResponse:
        query = self._session.query(TradingHalt)
        normalized_status = status.lower() if status else None
        if normalized_status is not None:
            query = query.filter(TradingHalt.status == normalized_status)

        total = query.count()
        items = (
            query.order_by(TradingHalt.triggered_at.desc(), TradingHalt.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return TradingHaltListResponse(
            items=[TradingHaltResponse.model_validate(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
            status_filter=normalized_status,
        )

    def is_halt_active(self, scope: str = "global") -> bool:
        return self.get_active_halt(scope=scope) is not None

    def build_blocked_reason(self, scope: str = "global") -> str | None:
        active_halt = self.get_active_halt(scope=scope)
        if active_halt is None:
            return None

        detail = active_halt.reason or "No reason recorded."
        return f"Trading halt active ({active_halt.halt_type}) for scope '{active_halt.scope}': {detail}"