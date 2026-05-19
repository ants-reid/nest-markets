"""Thin signal API routes for safe MVP wiring."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.clients.llm.router import LLMProviderRouter
from app.db.models.feature_snapshot import FeatureSnapshot
from app.db.session import get_db_session
from app.schemas.signal import MockGenerateSignalRequest, SignalResponse
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.signal_service import SignalInput, SignalService

router = APIRouter(prefix="/signals", tags=["signals"])


class GenerateSignalRequest(BaseModel):
    """Request schema for real LLM-backed signal generation."""

    model_config = ConfigDict(extra="forbid")

    asset: str
    timeframe: Literal["15m", "1h", "4h", "1d"]
    latest_price: float = Field(ge=0)
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)
    catalyst_context: dict[str, Any] = Field(default_factory=dict)
    risk_notes: str | None = None


@router.post("/mock-generate", response_model=SignalResponse)
def mock_generate_signal(request: MockGenerateSignalRequest) -> SignalResponse:
    """Return a mocked signal payload without calling the real LLM."""
    if request.mocked_signal is not None:
        return request.mocked_signal

    return SignalResponse(
        asset=request.asset,
        timeframe=request.timeframe,
        direction="flat",
        regime="range",
        setup_type="none",
        entry_zone=(0.0, 0.0),
        stop_price=0.0,
        target_price=0.0,
        confidence=0.0,
        horizon_label="intraday",
        catalyst_type="none",
        catalyst_score=0.0,
        catalyst_summary="Mock-safe route: no catalyst evaluated.",
        thesis=f"Mock-safe no-trade response for {request.asset} at {request.latest_price}.",
        invalidators=["No trade"],
        signal_score=0.0,
        should_trade=False,
    )


@router.post("/generate", response_model=SignalResponse)
async def generate_signal(
    request: GenerateSignalRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> SignalResponse:
    """Generate a real structured signal using the configured LLM provider.

    Requires OPENAI_API_KEY (or equivalent) to be configured in the server
    environment. Use /signals/mock-generate for safe development/testing.
    After generation, the signal is persisted to the database and the
    returned response includes the persisted signal_id.
    """
    settings = get_settings()
    router_llm = LLMProviderRouter(settings)
    service = SignalService(router=router_llm, session=session)

    signal_input = SignalInput(
        asset=request.asset,
        timeframe=request.timeframe,
        latest_price=request.latest_price,
        feature_snapshot=request.feature_snapshot,
        catalyst_context=request.catalyst_context,
        risk_notes=request.risk_notes,
    )

    result = await service.generate_signal(signal_input)

    # Persist to DB and capture the assigned signal ID
    persistence = PersistenceSignalService(session)
    try:
        persisted = persistence.persist_signal(
            result,
            prompt_version_id=service.get_last_prompt_version_id(),
            model_version_id=service.get_last_model_version_id(),
        )
        session.commit()
        persisted_id = persisted.id
    except Exception:
        session.rollback()
        persisted_id = None

    return SignalResponse(
        signal_id=persisted_id,
        asset=result.asset,
        timeframe=result.timeframe,
        direction=result.direction,
        regime=result.regime,
        setup_type=result.setup_type,
        entry_zone=result.entry_zone,
        stop_price=result.stop_price,
        target_price=result.target_price,
        confidence=result.confidence,
        horizon_label=result.horizon_label,
        catalyst_type=result.catalyst_type,
        catalyst_score=result.catalyst_score,
        catalyst_summary=result.catalyst_summary,
        thesis=result.thesis,
        invalidators=result.invalidators,
        signal_score=result.signal_score,
        should_trade=result.should_trade,
    )


class FeatureSnapshotResponse(BaseModel):
    """Flat representation of a persisted feature snapshot row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    signal_id: UUID | None
    scan_ts: Any
    timeframe: str
    trend_score: float | None
    momentum_score: float | None
    volatility_score: float | None
    liquidity_score: float | None
    regime: str | None
    atr: float | None
    rsi: float | None
    ema_fast: float | None
    ema_slow: float | None
    adx: float | None
    market_quality_flag: str | None


@router.get("/{signal_id}/features", response_model=FeatureSnapshotResponse)
def get_signal_features(
    signal_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> FeatureSnapshotResponse:
    """Return the feature snapshot linked to a specific signal.

    Returns 404 if no feature snapshot exists for the given signal ID.
    """
    stmt = select(FeatureSnapshot).where(FeatureSnapshot.signal_id == signal_id)
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No feature snapshot found for signal '{signal_id}'")
    return FeatureSnapshotResponse(
        id=row.id,
        asset_id=row.asset_id,
        signal_id=row.signal_id,
        scan_ts=row.scan_ts,
        timeframe=row.timeframe,
        trend_score=float(row.trend_score) if row.trend_score is not None else None,
        momentum_score=float(row.momentum_score) if row.momentum_score is not None else None,
        volatility_score=float(row.volatility_score) if row.volatility_score is not None else None,
        liquidity_score=float(row.liquidity_score) if row.liquidity_score is not None else None,
        regime=row.regime.value if row.regime is not None else None,
        atr=float(row.atr) if row.atr is not None else None,
        rsi=float(row.rsi) if row.rsi is not None else None,
        ema_fast=float(row.ema_fast) if row.ema_fast is not None else None,
        ema_slow=float(row.ema_slow) if row.ema_slow is not None else None,
        adx=float(row.adx) if row.adx is not None else None,
        market_quality_flag=row.market_quality_flag,
    )
