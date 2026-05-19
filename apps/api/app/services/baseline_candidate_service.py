"""Baseline candidate service for MH-15 research-stage workflow."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models.baseline_candidate import BaselineCandidate
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.schemas.strategy_lab import (
    BaselineCandidateCreateRequest,
    BaselineCandidateListResponse,
    BaselineCandidateResponse,
    BaselineCandidateUpdateRequest,
)

_ACTIVE_STATUSES = {"watchlist_candidate", "baseline_candidate", "needs_more_testing"}


class BaselineCandidateError(Exception):
    """Controlled baseline candidate failures."""


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BaselineCandidateService:
    """CRUD operations for baseline candidates (research-stage only)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _load_result_and_config(
        self,
        backtest_run_id: uuid.UUID,
        strategy_config_id: uuid.UUID,
    ) -> tuple[StrategyResult, StrategyConfig]:
        result = self._session.execute(
            select(StrategyResult).where(
                and_(
                    StrategyResult.backtest_run_id == backtest_run_id,
                    StrategyResult.strategy_config_id == strategy_config_id,
                )
            )
        ).scalars().first()
        if result is None:
            raise BaselineCandidateError("Strategy result not found for given backtest/config")

        config = self._session.get(StrategyConfig, strategy_config_id)
        if config is None:
            raise BaselineCandidateError("Strategy config not found")

        return result, config

    def _ensure_no_duplicate_active_candidate(
        self,
        backtest_run_id: uuid.UUID,
        strategy_config_id: uuid.UUID,
    ) -> None:
        existing = self._session.execute(
            select(BaselineCandidate).where(
                and_(
                    BaselineCandidate.backtest_run_id == backtest_run_id,
                    BaselineCandidate.strategy_config_id == strategy_config_id,
                    BaselineCandidate.status.in_(_ACTIVE_STATUSES),
                )
            )
        ).scalars().first()
        if existing is not None:
            raise BaselineCandidateError("Active baseline candidate already exists for this run/config")

    def create_candidate(
        self,
        body: BaselineCandidateCreateRequest,
    ) -> BaselineCandidateResponse:
        run_id = uuid.UUID(body.backtest_run_id)
        config_id = uuid.UUID(body.strategy_config_id)

        self._ensure_no_duplicate_active_candidate(run_id, config_id)
        result, config = self._load_result_and_config(run_id, config_id)

        metrics = {
            "total_trades": result.total_trades,
            "win_rate": _to_float(result.win_rate),
            "profit_factor": _to_float(result.profit_factor),
            "total_return_pct": _to_float(result.total_return_pct),
            "max_drawdown_pct": _to_float(result.max_drawdown_pct),
            "score": _to_float(result.score),
            "asset": result.asset,
            "timeframe": result.timeframe,
        }

        candidate = BaselineCandidate(
            backtest_run_id=run_id,
            strategy_config_id=config_id,
            ai_backtest_report_id=uuid.UUID(body.ai_backtest_report_id) if body.ai_backtest_report_id else None,
            asset=result.asset or config.asset,
            timeframe=result.timeframe or config.timeframe,
            strategy_type=config.strategy_type,
            parameters=dict(config.parameters or {}),
            metrics=metrics,
            status=body.status,
            review_notes=body.review_notes,
            created_by=body.created_by,
        )
        self._session.add(candidate)
        self._session.commit()
        self._session.refresh(candidate)
        return BaselineCandidateResponse.model_validate(candidate)

    def list_candidates(
        self,
        status: str | None = None,
        backtest_run_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> BaselineCandidateListResponse:
        stmt = select(BaselineCandidate)
        if status:
            stmt = stmt.where(BaselineCandidate.status == status)
        if backtest_run_id:
            stmt = stmt.where(BaselineCandidate.backtest_run_id == uuid.UUID(backtest_run_id))

        rows = self._session.execute(
            stmt.order_by(BaselineCandidate.created_at.desc()).limit(limit).offset(offset)
        ).scalars().all()

        return BaselineCandidateListResponse(
            total=len(rows),
            items=[BaselineCandidateResponse.model_validate(r) for r in rows],
        )

    def get_candidate(self, candidate_id: str) -> BaselineCandidateResponse | None:
        row = self._session.get(BaselineCandidate, uuid.UUID(candidate_id))
        if row is None:
            return None
        return BaselineCandidateResponse.model_validate(row)

    def update_candidate(
        self,
        candidate_id: str,
        body: BaselineCandidateUpdateRequest,
    ) -> BaselineCandidateResponse | None:
        row = self._session.get(BaselineCandidate, uuid.UUID(candidate_id))
        if row is None:
            return None

        if body.status is not None:
            row.status = body.status
        if body.review_notes is not None:
            row.review_notes = body.review_notes
        if body.reviewed_by is not None:
            row.reviewed_by = body.reviewed_by

        if body.status is not None or body.reviewed_by is not None:
            row.reviewed_at = datetime.now(timezone.utc)

        self._session.commit()
        self._session.refresh(row)
        return BaselineCandidateResponse.model_validate(row)

    def reject_candidate(
        self,
        candidate_id: str,
        reviewed_by: str | None,
        review_notes: str | None,
    ) -> BaselineCandidateResponse | None:
        row = self._session.get(BaselineCandidate, uuid.UUID(candidate_id))
        if row is None:
            return None

        row.status = "rejected"
        row.reviewed_by = reviewed_by
        row.review_notes = review_notes
        row.reviewed_at = datetime.now(timezone.utc)

        self._session.commit()
        self._session.refresh(row)
        return BaselineCandidateResponse.model_validate(row)
