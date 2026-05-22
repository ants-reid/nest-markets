"""Thin execution API routes for MVP paper and live scaffolding."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, select

from app.db.enums import OrderStatus, PositionStatus
from app.middleware.auth import api_key_auth
from app.middleware.idempotency import check_idempotency_key, release_idempotency_key
from app.services import audit_log_service
from app.db.models.asset import Asset
from app.db.models.pnl_snapshot import PnlSnapshot
from app.db.models.position import Position
from app.db.models.signal import Signal as SignalModel
from app.db.session import get_db_session
from app.schemas.execution import (
    LiveExecutionRequestSchema,
    LiveExecutionResponse,
    PaperExecutionRequest,
    PaperExecutionResponse,
)
from app.services.execution_journal_service import ExecutionJournalService
from app.services.live_execution_service import LiveExecutionRequest, LiveExecutionService
from app.services.pnl_service import PnlService, PnlSnapshotInput
from app.services.persistence_paper_execution_service import PersistencePaperExecutionService
from app.services.paper_execution_service import StatelessPaperExecutionService as PaperExecutionService
from app.services.position_service import OpenPositionInput, PositionService
from app.services.signal_service import SignalOutput
from app.services.visual_seed import VISUAL_SEED_PROVIDER

router = APIRouter(prefix="/execution", tags=["execution"])


def _to_paper_execution_response(result) -> PaperExecutionResponse:
    payload = dict(result.__dict__)
    payload.update(
        {
            "execution_source": "internal_mock_simulator",
            "balance_source": "app_simulated",
            "fees_source": "estimated",
            "fills_source": "simulated",
        }
    )
    return PaperExecutionResponse(**payload)


class PaperExecutionJournalUpsertRequest(BaseModel):
    """Typed request payload for backend-backed execution journal saves."""

    outcome_tag: Literal["untagged", "worked", "partial", "stopped_out", "expired", "invalidated"]
    note: str = ""
    tags: list[str] = Field(default_factory=list)


class PaperExecutionJournalResponse(BaseModel):
    """Typed response payload for backend-backed execution journal reads."""

    execution_id: UUID
    outcome_tag: Literal["untagged", "worked", "partial", "stopped_out", "expired", "invalidated"]
    note: str
    tags: list[str]
    updated_at: str


class PositionResponse(BaseModel):
    id: UUID
    asset_id: UUID
    asset_symbol: str
    signal_id: UUID | None
    status: str
    side: str
    avg_entry_price: float | None
    current_price: float | None
    stop_price: float | None
    target_price: float | None
    qty: float | None
    opened_at: datetime | None
    closed_at: datetime | None
    close_reason: str | None
    realized_pnl: float | None
    unrealized_pnl: float | None


class PositionPnlSnapshotResponse(BaseModel):
    id: UUID
    snapshot_ts: datetime
    equity: float | None
    cash: float | None
    gross_exposure: float | None
    net_exposure: float | None
    open_pnl: float | None
    closed_pnl: float | None
    drawdown_pct: float | None
    metadata_json: dict | None


def _get_execution_journal_service() -> ExecutionJournalService:
    """Build the MVP execution journal service."""
    return ExecutionJournalService()


def _get_paper_order_or_404(session: Session, execution_id: UUID):
    """Return one persisted paper order row or raise a route-friendly 404."""
    persistence = PersistencePaperExecutionService(session)
    row = persistence.get_paper_order(execution_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Paper order '{execution_id}' not found")
    return row


def _position_response(session: Session, row: Position) -> PositionResponse:
    asset = session.get(Asset, row.asset_id)
    return PositionResponse(
        id=row.id,
        asset_id=row.asset_id,
        asset_symbol=asset.symbol if asset is not None else "unknown",
        signal_id=row.signal_id,
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        side=row.side,
        avg_entry_price=float(row.avg_entry_price) if row.avg_entry_price is not None else None,
        current_price=float(row.current_price) if row.current_price is not None else None,
        stop_price=float(row.stop_price) if row.stop_price is not None else None,
        target_price=float(row.target_price) if row.target_price is not None else None,
        qty=float(row.qty) if row.qty is not None else None,
        opened_at=row.opened_at,
        closed_at=row.closed_at,
        close_reason=row.close_reason,
        realized_pnl=float(row.realized_pnl) if row.realized_pnl is not None else None,
        unrealized_pnl=float(row.unrealized_pnl) if row.unrealized_pnl is not None else None,
    )


def _position_pnl_response(row: PnlSnapshot) -> PositionPnlSnapshotResponse:
    return PositionPnlSnapshotResponse(
        id=row.id,
        snapshot_ts=row.snapshot_ts,
        equity=float(row.equity) if row.equity is not None else None,
        cash=float(row.cash) if row.cash is not None else None,
        gross_exposure=float(row.gross_exposure) if row.gross_exposure is not None else None,
        net_exposure=float(row.net_exposure) if row.net_exposure is not None else None,
        open_pnl=float(row.open_pnl) if row.open_pnl is not None else None,
        closed_pnl=float(row.closed_pnl) if row.closed_pnl is not None else None,
        drawdown_pct=float(row.drawdown_pct) if row.drawdown_pct is not None else None,
        metadata_json=row.metadata_json,
    )


@router.post("/paper", response_model=PaperExecutionResponse)
def execute_paper(
    request: PaperExecutionRequest,
    _: Annotated[str, Depends(api_key_auth)] = None,
    idempotency_key: Annotated[str | None, Depends(check_idempotency_key)] = None,
) -> PaperExecutionResponse:
    """Simulate paper execution using existing deterministic service logic."""
    signal = SignalOutput(**request.signal.model_dump(exclude={"signal_id"}))
    try:
        result = PaperExecutionService().submit_order(
            signal=signal,
            allowed_risk_amount=request.allowed_risk_amount,
            latest_price=request.latest_price,
        )
    except Exception:
        if idempotency_key:
            release_idempotency_key(idempotency_key)
        raise
    audit_log_service.log_trade_submitted(
        endpoint="/execution/paper",
        asset=signal.asset,
        side=result.side if result else "unknown",
        qty=result.qty if result else None,
        notional=result.notional if result else None,
        idempotency_key=idempotency_key,
    )
    return _to_paper_execution_response(result)


@router.get("/positions", response_model=list[PositionResponse])
def list_positions(
    session: Annotated[Session, Depends(get_db_session)],
    include_visual_seed: Annotated[bool, Query(description="Include visual seed demo data")] = False,
) -> list[PositionResponse]:
    """Return all currently open positions."""
    statement = (
        select(Position)
        .where(Position.status == PositionStatus.OPEN)
        .order_by(Position.created_at.asc(), Position.id.asc())
    )

    if not include_visual_seed:
        statement = (
            statement
            .outerjoin(SignalModel, Position.signal_id == SignalModel.id)
            .where(
                or_(
                    Position.signal_id.is_(None),
                    SignalModel.provider_name.is_(None),
                    SignalModel.provider_name != VISUAL_SEED_PROVIDER,
                )
            )
        )

    rows = session.execute(statement).scalars().all()
    return [_position_response(session, row) for row in rows]


@router.get("/positions/{position_id}/pnl", response_model=list[PositionPnlSnapshotResponse])
def get_position_pnl(
    position_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> list[PositionPnlSnapshotResponse]:
    """Return recorded PnL snapshots for a position."""
    position = session.get(Position, position_id)
    if position is None:
        raise HTTPException(status_code=404, detail=f"Position '{position_id}' not found")

    rows = (
        session.execute(select(PnlSnapshot).order_by(PnlSnapshot.snapshot_ts.asc()))
        .scalars()
        .all()
    )
    filtered = [
        row for row in rows
        if isinstance(row.metadata_json, dict) and str(row.metadata_json.get("position_id")) == str(position_id)
    ]
    return [_position_pnl_response(row) for row in filtered]


@router.post("/positions/{position_id}/snapshot", response_model=PositionPnlSnapshotResponse)
def snapshot_position_pnl(
    position_id: UUID,
    mark_price: float,
    session: Annotated[Session, Depends(get_db_session)],
) -> PositionPnlSnapshotResponse:
    """Mark a position to market and record a PnL snapshot."""
    position = session.get(Position, position_id)
    if position is None:
        raise HTTPException(status_code=404, detail=f"Position '{position_id}' not found")

    position_result = PositionService(session).mark_to_market(position_id, mark_price)
    snapshot = PnlService(session).record_snapshot(
        PnlSnapshotInput(
            equity=position_result.unrealized_pnl or 0.0,
            open_pnl=position_result.unrealized_pnl,
            closed_pnl=position_result.realized_pnl,
            metadata_json={
                "position_id": str(position_id),
                "mark_price": mark_price,
                "side": position_result.side,
            },
            snapshot_ts=datetime.now(UTC),
        )
    )
    session.commit()
    row = session.get(PnlSnapshot, snapshot.id)
    assert row is not None
    return _position_pnl_response(row)


@router.get("/paper", response_model=list[PaperExecutionResponse])
def list_paper_orders(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: str | None = None,
    include_visual_seed: Annotated[bool, Query(description="Include visual seed demo data")] = False,
) -> list[PaperExecutionResponse]:
    """Return persisted paper orders for list views with simple filtering and paging."""
    parsed_status: OrderStatus | None = None
    if status is not None:
        try:
            parsed_status = OrderStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Unsupported order status '{status}'") from exc

    persistence = PersistencePaperExecutionService(session)
    rows = persistence.list_paper_orders(
        limit=limit,
        offset=offset,
        status=parsed_status,
        include_visual_seed=include_visual_seed,
    )

    results: list[PaperExecutionResponse] = []
    for row in rows:
        try:
            result = persistence.build_service_result(row)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        results.append(_to_paper_execution_response(result))

    return results


@router.get("/paper/{execution_id}", response_model=PaperExecutionResponse)
def get_paper_order(
    execution_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperExecutionResponse:
    """Return one persisted paper order as a typed paper execution response."""
    persistence = PersistencePaperExecutionService(session)
    row = _get_paper_order_or_404(session, execution_id)

    try:
        result = persistence.build_service_result(row)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_paper_execution_response(result)


@router.get("/paper/{execution_id}/history", response_model=dict[str, object])
def get_paper_order_history(
    execution_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    """Return ordered lifecycle events for one persisted paper order."""
    persistence = PersistencePaperExecutionService(session)
    row = _get_paper_order_or_404(session, execution_id)

    events = persistence.build_history_events(row)
    return {"execution_id": row.id, "events": events}


@router.post("/paper/{execution_id}/fill", response_model=PaperExecutionResponse)
def fill_paper_order(
    execution_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperExecutionResponse:
    """Advance one persisted paper order from submitted to filled."""
    persistence = PersistencePaperExecutionService(session)
    row = _get_paper_order_or_404(session, execution_id)

    try:
        submitted = persistence.build_service_result(row)
        filled = PaperExecutionService().fill_order(submitted)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    persistence.persist_paper_execution(row.signal_id, filled)
    signal = session.get(SignalModel, row.signal_id)
    if signal is not None:
        existing_position = (
            session.execute(
                select(Position).where(
                    Position.signal_id == signal.id,
                    Position.status == PositionStatus.OPEN,
                )
            )
            .scalars()
            .first()
        )
        if existing_position is None:
            PositionService(session).open_position(
                OpenPositionInput(
                    asset_id=signal.asset_id,
                    signal_id=signal.id,
                    side=signal.direction.value if hasattr(signal.direction, "value") else str(signal.direction),
                    avg_entry_price=filled.fill_price,
                    qty=filled.qty,
                    stop_price=filled.stop_price,
                    target_price=filled.target_price,
                )
            )
    session.commit()
    return _to_paper_execution_response(filled)


@router.post("/paper/{execution_id}/close", response_model=PaperExecutionResponse)
def close_paper_order(
    execution_id: UUID,
    close_price: float,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperExecutionResponse:
    """Advance one persisted paper order from filled to closed."""
    persistence = PersistencePaperExecutionService(session)
    row = _get_paper_order_or_404(session, execution_id)

    try:
        filled = persistence.build_service_result(row)
        closed = PaperExecutionService().close_order(filled, close_price=close_price)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    persistence.persist_paper_execution(row.signal_id, closed)
    signal = session.get(SignalModel, row.signal_id)
    if signal is not None:
        position = (
            session.execute(
                select(Position).where(
                    Position.signal_id == signal.id,
                    Position.status == PositionStatus.OPEN,
                )
            )
            .scalars()
            .first()
        )
        if position is not None:
            PositionService(session).close_position(position.id, close_price=close_price, close_reason="paper_order_closed")
    session.commit()
    return _to_paper_execution_response(closed)


@router.get("/paper/{execution_id}/journal", response_model=PaperExecutionJournalResponse)
def get_paper_order_journal(
    execution_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperExecutionJournalResponse:
    """Return one backend-backed journal entry for a persisted paper order."""
    _get_paper_order_or_404(session, execution_id)
    journal = _get_execution_journal_service().get_journal(execution_id)
    if journal is None:
        raise HTTPException(status_code=404, detail=f"Journal for paper order '{execution_id}' not found")
    return PaperExecutionJournalResponse(**asdict(journal))


@router.put("/paper/{execution_id}/journal", response_model=PaperExecutionJournalResponse)
def upsert_paper_order_journal(
    execution_id: UUID,
    payload: PaperExecutionJournalUpsertRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> PaperExecutionJournalResponse:
    """Create or update one backend-backed journal entry for a persisted paper order."""
    _get_paper_order_or_404(session, execution_id)
    journal = _get_execution_journal_service().upsert_journal(
        execution_id,
        outcome_tag=payload.outcome_tag,
        note=payload.note,
        tags=payload.tags,
    )
    return PaperExecutionJournalResponse(**asdict(journal))


@router.post("/live", response_model=LiveExecutionResponse)
def execute_live(request: LiveExecutionRequestSchema) -> LiveExecutionResponse:
    """Return the disabled live execution scaffold response for MVP."""
    live_request = LiveExecutionRequest(**request.model_dump())
    result = LiveExecutionService().submit(live_request)
    result_data = {k: v for k, v in result.__dict__.items() if k in LiveExecutionResponse.model_fields}
    result_data.update(
        {
            "execution_source": "ibkr_live_locked",
            "balance_source": "ibkr_live_locked",
            "fees_source": "unavailable",
            "fills_source": "unavailable",
        }
    )
    return LiveExecutionResponse(**result_data)
