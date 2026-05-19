"""Paper validation gate service for MH-16/MH-17.

This service is intentionally isolated from live execution and broker flows.
It only tracks plan requirements/progress and deterministic pass/fail outcomes.
MH-17 adds evidence ingestion and reconciliation from existing paper records.
No live trading decisions are made here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.baseline_candidate import BaselineCandidate
from app.db.models.paper_validation_event import PaperValidationEvent
from app.db.models.paper_validation_evidence import PaperValidationEvidence
from app.db.models.paper_validation_plan import PaperValidationPlan
from app.db.models.signal import Signal
from app.db.models.signal_outcome import SignalOutcome
from app.schemas.strategy_lab import (
    PaperValidationEvidenceListResponse,
    PaperValidationEvidenceResponse,
    PaperValidationEventResponse,
    PaperValidationManualEvidenceRequest,
    PaperValidationPlanActionRequest,
    PaperValidationPlanCreateRequest,
    PaperValidationPlanListResponse,
    PaperValidationPlanResponse,
    PaperValidationPlanUpdateRequest,
    PaperValidationProgressResponse,
    PaperValidationReconcileRequest,
    PaperValidationReconcileResponse,
)

if TYPE_CHECKING:
    from app.schemas.strategy_lab import (
        PaperValidationDashboardResponse,
        PaperValidationReadinessResponse,
    )

_VALID_STATUSES = {"pending", "active", "passed", "failed", "stopped"}
_MANUAL_UPDATE_STATUSES = {"pending", "active", "stopped"}


class PaperValidationError(Exception):
    """Controlled paper validation failures."""


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PaperValidationService:
    """Application service for MH-16 paper validation plans."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _add_event(
        self,
        plan_id: uuid.UUID,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            PaperValidationEvent(
                paper_validation_plan_id=plan_id,
                event_type=event_type,
                message=message,
                payload=payload,
            )
        )

    def _compute_progress_from_evidence(
        self,
        plan: PaperValidationPlan,
        evidence_rows: list[PaperValidationEvidence],
    ) -> PaperValidationProgressResponse:
        """Compute progress metrics from included evidence records."""
        included = [e for e in evidence_rows if e.included_in_metrics]

        wins = sum(1 for e in included if e.result == "win")
        losses = sum(1 for e in included if e.result == "loss")
        breakeven = sum(1 for e in included if e.result == "breakeven")
        total_paper_trades = wins + losses + breakeven

        win_rate: float | None = None
        denominator = wins + losses + breakeven
        if denominator > 0:
            win_rate = wins / denominator

        # Profit factor from pnl_amount
        gross_profit = sum(
            float(e.pnl_amount) for e in included
            if e.pnl_amount is not None and float(e.pnl_amount) > 0
        )
        gross_loss = abs(sum(
            float(e.pnl_amount) for e in included
            if e.pnl_amount is not None and float(e.pnl_amount) < 0
        ))
        profit_factor: float | None = None
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = None  # no losses yet; can't compute meaningful PF

        # Total return from pnl_pct
        pnl_pcts = [float(e.pnl_pct) for e in included if e.pnl_pct is not None]
        total_return_pct: float | None = sum(pnl_pcts) if pnl_pcts else None

        # Max drawdown from cumulative equity curve approximation
        max_drawdown_pct: float | None = None
        if len(pnl_pcts) >= 3:
            equity = 0.0
            peak = 0.0
            max_dd = 0.0
            for p in pnl_pcts:
                equity += p
                if equity > peak:
                    peak = equity
                dd = peak - equity
                if dd > max_dd:
                    max_dd = dd
            max_drawdown_pct = max_dd if max_dd > 0 else None

        # Fall back to plan.paper_metrics for max_drawdown if evidence is insufficient
        if max_drawdown_pct is None and plan.paper_metrics:
            max_drawdown_pct = _to_float((plan.paper_metrics or {}).get("max_drawdown_pct"))

        days_active = _to_int((plan.paper_metrics or {}).get("days_active"))
        if days_active == 0 and plan.started_at is not None:
            delta_days = (_now() - plan.started_at).days
            days_active = max(1, delta_days + 1)

        progress_trades_pct = min(100.0, (total_paper_trades / max(1, plan.required_trades)) * 100.0)
        progress_days_pct = min(100.0, (days_active / max(1, plan.minimum_days)) * 100.0)

        # Reuse the same pass/fail rule evaluation
        reasons: list[str] = []
        pass_fail_status = "pending"

        if plan.status == "stopped":
            pass_fail_status = "stopped"
            reasons.append("Validation plan stopped manually.")
        else:
            if plan.max_drawdown_pct is not None and max_drawdown_pct is not None:
                if max_drawdown_pct > float(plan.max_drawdown_pct):
                    reasons.append(
                        f"Max drawdown {max_drawdown_pct:.2f}% exceeded threshold {float(plan.max_drawdown_pct):.2f}%"
                    )
            if plan.target_profit_factor is not None and profit_factor is not None:
                if profit_factor < float(plan.target_profit_factor):
                    reasons.append(
                        f"Profit factor {profit_factor:.3f} below target {float(plan.target_profit_factor):.3f}"
                    )
            if reasons:
                pass_fail_status = "failed"
            else:
                trades_met = total_paper_trades >= plan.required_trades
                days_met = days_active >= plan.minimum_days
                if trades_met and days_met:
                    pass_fail_status = "passed"
                elif plan.started_at is None:
                    pass_fail_status = "pending"
                else:
                    pass_fail_status = "active"

        return PaperValidationProgressResponse(
            total_paper_trades=total_paper_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            days_active=days_active,
            progress_trades_pct=progress_trades_pct,
            progress_days_pct=progress_days_pct,
            pass_fail_status=pass_fail_status,
            reasons=reasons,
        )

    def _compute_progress(self, plan: PaperValidationPlan) -> PaperValidationProgressResponse:
        # MH-17: if there is evidence for this plan, compute metrics from it
        evidence_rows: list[PaperValidationEvidence] = []
        if plan.id is not None:
            evidence_rows = list(
                self._session.execute(
                    select(PaperValidationEvidence).where(
                        PaperValidationEvidence.paper_validation_plan_id == plan.id
                    )
                ).scalars().all()
            )
        if evidence_rows:
            return self._compute_progress_from_evidence(plan, evidence_rows)

        # Fall back to manual paper_metrics dict (MH-16 behaviour)
        metrics = dict(plan.paper_metrics or {})

        total_paper_trades = _to_int(metrics.get("total_paper_trades"))
        wins = _to_int(metrics.get("wins"))
        losses = _to_int(metrics.get("losses"))

        win_rate = _to_float(metrics.get("win_rate"))
        if win_rate is None and total_paper_trades > 0:
            win_rate = wins / total_paper_trades

        profit_factor = _to_float(metrics.get("profit_factor"))
        total_return_pct = _to_float(metrics.get("total_return_pct"))
        max_drawdown_pct = _to_float(metrics.get("max_drawdown_pct"))
        max_daily_loss_pct = _to_float(metrics.get("max_daily_loss_pct"))

        days_active = _to_int(metrics.get("days_active"))
        if days_active == 0 and plan.started_at is not None:
            delta_days = (_now() - plan.started_at).days
            days_active = max(1, delta_days + 1)

        progress_trades_pct = min(100.0, (total_paper_trades / max(1, plan.required_trades)) * 100.0)
        progress_days_pct = min(100.0, (days_active / max(1, plan.minimum_days)) * 100.0)

        reasons: list[str] = []
        pass_fail_status = "pending"

        if plan.status == "stopped":
            pass_fail_status = "stopped"
            reasons.append("Validation plan stopped manually.")
        else:
            if plan.max_drawdown_pct is not None and max_drawdown_pct is not None:
                if max_drawdown_pct > float(plan.max_drawdown_pct):
                    reasons.append(
                        f"Max drawdown {max_drawdown_pct:.2f}% exceeded threshold {float(plan.max_drawdown_pct):.2f}%"
                    )

            if plan.max_daily_loss_pct is not None and max_daily_loss_pct is not None:
                if max_daily_loss_pct > float(plan.max_daily_loss_pct):
                    reasons.append(
                        f"Max daily loss {max_daily_loss_pct:.2f}% exceeded threshold {float(plan.max_daily_loss_pct):.2f}%"
                    )

            if plan.target_profit_factor is not None and profit_factor is not None:
                if profit_factor < float(plan.target_profit_factor):
                    reasons.append(
                        f"Profit factor {profit_factor:.3f} below target {float(plan.target_profit_factor):.3f}"
                    )

            if reasons:
                pass_fail_status = "failed"
            else:
                trades_met = total_paper_trades >= plan.required_trades
                days_met = days_active >= plan.minimum_days
                if trades_met and days_met:
                    pass_fail_status = "passed"
                elif plan.started_at is None:
                    pass_fail_status = "pending"
                else:
                    pass_fail_status = "active"

        return PaperValidationProgressResponse(
            total_paper_trades=total_paper_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            days_active=days_active,
            progress_trades_pct=progress_trades_pct,
            progress_days_pct=progress_days_pct,
            pass_fail_status=pass_fail_status,
            reasons=reasons,
        )

    def _apply_deterministic_status(self, plan: PaperValidationPlan, computed: PaperValidationProgressResponse) -> None:
        if plan.status == "stopped":
            return

        if computed.pass_fail_status == "failed":
            plan.status = "failed"
            if plan.completed_at is None:
                plan.completed_at = _now()
            return

        if computed.pass_fail_status == "passed":
            plan.status = "passed"
            if plan.completed_at is None:
                plan.completed_at = _now()
            return

        if plan.started_at is None:
            plan.status = "pending"
        elif plan.status in {"pending", "active"}:
            plan.status = "active"

    def _recalculate_in_place(self, plan: PaperValidationPlan) -> PaperValidationProgressResponse:
        computed = self._compute_progress(plan)
        self._apply_deterministic_status(plan, computed)
        plan.progress = computed.model_dump()
        plan.pass_fail_reasons = computed.reasons
        return computed

    def _load_plan(self, plan_id: str) -> PaperValidationPlan:
        plan = self._session.get(PaperValidationPlan, uuid.UUID(plan_id))
        if plan is None:
            raise PaperValidationError("Paper validation plan not found")
        return plan

    def create_plan(self, body: PaperValidationPlanCreateRequest) -> PaperValidationPlanResponse:
        candidate = self._session.get(BaselineCandidate, uuid.UUID(body.baseline_candidate_id))
        if candidate is None:
            raise PaperValidationError("Baseline candidate not found")

        active_existing = self._session.execute(
            select(PaperValidationPlan).where(
                and_(
                    PaperValidationPlan.baseline_candidate_id == candidate.id,
                    PaperValidationPlan.status.in_(["pending", "active"]),
                )
            )
        ).scalars().first()
        if active_existing is not None:
            raise PaperValidationError("Active paper validation plan already exists for this baseline candidate")

        candidate_metrics = dict(candidate.metrics or {})
        plan = PaperValidationPlan(
            baseline_candidate_id=candidate.id,
            backtest_run_id=candidate.backtest_run_id,
            strategy_config_id=candidate.strategy_config_id,
            status="pending",
            required_trades=body.required_trades,
            minimum_days=body.minimum_days,
            target_profit_factor=(
                body.target_profit_factor
                if body.target_profit_factor is not None
                else _to_float(candidate_metrics.get("profit_factor"))
            ),
            max_drawdown_pct=(
                body.max_drawdown_pct
                if body.max_drawdown_pct is not None
                else _to_float(candidate_metrics.get("max_drawdown_pct"))
            ),
            max_daily_loss_pct=body.max_daily_loss_pct,
            starting_paper_capital=body.starting_paper_capital,
            backtest_metrics=candidate_metrics,
            paper_metrics=None,
            created_by=body.created_by,
            review_notes=body.review_notes,
        )
        self._session.add(plan)
        self._session.flush()

        self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "plan_created",
            "Paper validation plan created from baseline candidate.",
            payload={
                "baseline_candidate_id": str(candidate.id),
                "required_trades": body.required_trades,
                "minimum_days": body.minimum_days,
            },
        )

        self._session.commit()
        self._session.refresh(plan)
        return PaperValidationPlanResponse.model_validate(plan)

    def list_plans(
        self,
        status: str | None = None,
        baseline_candidate_id: str | None = None,
        backtest_run_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> PaperValidationPlanListResponse:
        stmt = select(PaperValidationPlan)
        if status:
            if status not in _VALID_STATUSES:
                raise PaperValidationError("Invalid status filter")
            stmt = stmt.where(PaperValidationPlan.status == status)
        if baseline_candidate_id:
            stmt = stmt.where(
                PaperValidationPlan.baseline_candidate_id == uuid.UUID(baseline_candidate_id)
            )
        if backtest_run_id:
            stmt = stmt.where(PaperValidationPlan.backtest_run_id == uuid.UUID(backtest_run_id))

        rows = self._session.execute(
            stmt.order_by(PaperValidationPlan.created_at.desc()).limit(limit).offset(offset)
        ).scalars().all()

        return PaperValidationPlanListResponse(
            total=len(rows),
            items=[PaperValidationPlanResponse.model_validate(r) for r in rows],
        )

    def get_plan(self, plan_id: str) -> PaperValidationPlanResponse:
        plan = self._load_plan(plan_id)
        return PaperValidationPlanResponse.model_validate(plan)

    def update_plan(
        self,
        plan_id: str,
        body: PaperValidationPlanUpdateRequest,
    ) -> PaperValidationPlanResponse:
        plan = self._load_plan(plan_id)

        if body.status is not None:
            if body.status not in _MANUAL_UPDATE_STATUSES:
                raise PaperValidationError(
                    "Status updates for passed/failed are deterministic-only. Use recalculate/start/stop flows."
                )
            plan.status = body.status
            if body.status == "pending":
                plan.started_at = None
                plan.completed_at = None
            if body.status == "stopped" and plan.completed_at is None:
                plan.completed_at = _now()

        if body.required_trades is not None:
            plan.required_trades = body.required_trades
        if body.minimum_days is not None:
            plan.minimum_days = body.minimum_days
        if body.target_profit_factor is not None:
            plan.target_profit_factor = body.target_profit_factor
        if body.max_drawdown_pct is not None:
            plan.max_drawdown_pct = body.max_drawdown_pct
        if body.max_daily_loss_pct is not None:
            plan.max_daily_loss_pct = body.max_daily_loss_pct
        if body.starting_paper_capital is not None:
            plan.starting_paper_capital = body.starting_paper_capital
        if body.paper_metrics is not None:
            plan.paper_metrics = dict(body.paper_metrics)
        if body.review_notes is not None:
            plan.review_notes = body.review_notes
        if body.reviewed_by is not None:
            plan.reviewed_by = body.reviewed_by

        computed = self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "plan_updated",
            "Paper validation plan updated.",
            payload={"pass_fail_status": computed.pass_fail_status},
        )

        self._session.commit()
        self._session.refresh(plan)
        return PaperValidationPlanResponse.model_validate(plan)

    def start_plan(
        self,
        plan_id: str,
        body: PaperValidationPlanActionRequest,
    ) -> PaperValidationPlanResponse:
        plan = self._load_plan(plan_id)
        if plan.status != "pending":
            raise PaperValidationError("Only pending plans can be started")

        plan.status = "active"
        if plan.started_at is None:
            plan.started_at = _now()
        if body.reviewed_by is not None:
            plan.reviewed_by = body.reviewed_by
        if body.review_notes is not None:
            plan.review_notes = body.review_notes

        computed = self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "plan_started",
            "Paper validation plan started.",
            payload={"pass_fail_status": computed.pass_fail_status},
        )

        self._session.commit()
        self._session.refresh(plan)
        return PaperValidationPlanResponse.model_validate(plan)

    def stop_plan(
        self,
        plan_id: str,
        body: PaperValidationPlanActionRequest,
    ) -> PaperValidationPlanResponse:
        plan = self._load_plan(plan_id)
        if plan.status not in {"pending", "active"}:
            raise PaperValidationError("Only pending or active plans can be stopped")

        plan.status = "stopped"
        plan.completed_at = _now()
        if body.reviewed_by is not None:
            plan.reviewed_by = body.reviewed_by
        if body.review_notes is not None:
            plan.review_notes = body.review_notes

        computed = self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "plan_stopped",
            "Paper validation plan stopped.",
            payload={"pass_fail_status": computed.pass_fail_status},
        )

        self._session.commit()
        self._session.refresh(plan)
        return PaperValidationPlanResponse.model_validate(plan)

    def recalculate_plan(self, plan_id: str) -> PaperValidationPlanResponse:
        plan = self._load_plan(plan_id)
        computed = self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "plan_recalculated",
            "Paper validation progress recalculated.",
            payload={"pass_fail_status": computed.pass_fail_status},
        )

        self._session.commit()
        self._session.refresh(plan)
        return PaperValidationPlanResponse.model_validate(plan)

    def get_progress(self, plan_id: str) -> PaperValidationProgressResponse:
        plan = self._load_plan(plan_id)
        return self._compute_progress(plan)

    def list_events(self, plan_id: str) -> list[PaperValidationEventResponse]:
        plan_uuid = uuid.UUID(plan_id)
        rows = self._session.execute(
            select(PaperValidationEvent)
            .where(PaperValidationEvent.paper_validation_plan_id == plan_uuid)
            .order_by(PaperValidationEvent.created_at.asc())
        ).scalars().all()
        return [PaperValidationEventResponse.model_validate(r) for r in rows]

    # ── MH-17 Evidence / Reconciliation ──────────────────────────────────

    def add_manual_evidence(
        self,
        plan_id: str,
        body: PaperValidationManualEvidenceRequest,
    ) -> PaperValidationEvidenceResponse:
        plan = self._load_plan(plan_id)
        ev = PaperValidationEvidence(
            paper_validation_plan_id=plan.id,
            source_type="manual",
            source_id=None,
            confidence="manual",
            asset=body.asset,
            timeframe=body.timeframe,
            side=body.side,
            opened_at=body.opened_at,
            closed_at=body.closed_at,
            entry_price=body.entry_price,
            exit_price=body.exit_price,
            pnl_amount=body.pnl_amount,
            pnl_pct=body.pnl_pct,
            r_multiple=body.r_multiple,
            result=body.result,
            notes=body.notes,
            payload=body.payload,
            included_in_metrics=body.included_in_metrics,
        )
        self._session.add(ev)
        self._session.flush()

        self._add_event(
            plan.id,
            "evidence_added",
            f"Manual evidence added: {body.result}",
            payload={"source_type": "manual", "result": body.result, "pnl_pct": body.pnl_pct},
        )

        computed = self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "metrics_recalculated",
            "Metrics recalculated after manual evidence.",
            payload={"pass_fail_status": computed.pass_fail_status},
        )

        self._session.commit()
        self._session.refresh(ev)
        return PaperValidationEvidenceResponse.model_validate(ev)

    def list_evidence(self, plan_id: str) -> PaperValidationEvidenceListResponse:
        plan_uuid = uuid.UUID(plan_id)
        rows = list(
            self._session.execute(
                select(PaperValidationEvidence)
                .where(PaperValidationEvidence.paper_validation_plan_id == plan_uuid)
                .order_by(PaperValidationEvidence.created_at.desc())
            ).scalars().all()
        )
        return PaperValidationEvidenceListResponse(
            total=len(rows),
            items=[PaperValidationEvidenceResponse.model_validate(r) for r in rows],
        )

    def _load_evidence(self, plan_id: str, evidence_id: str) -> PaperValidationEvidence:
        plan_uuid = uuid.UUID(plan_id)
        ev_uuid = uuid.UUID(evidence_id)
        ev = self._session.get(PaperValidationEvidence, ev_uuid)
        if ev is None or ev.paper_validation_plan_id != plan_uuid:
            raise PaperValidationError("Evidence record not found for this plan")
        return ev

    def exclude_evidence(self, plan_id: str, evidence_id: str) -> PaperValidationEvidenceResponse:
        plan = self._load_plan(plan_id)
        ev = self._load_evidence(plan_id, evidence_id)
        ev.included_in_metrics = False

        self._add_event(
            plan.id,
            "evidence_excluded",
            f"Evidence {evidence_id[:8]} excluded from metrics.",
        )
        computed = self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "metrics_recalculated",
            "Metrics recalculated after evidence exclusion.",
            payload={"pass_fail_status": computed.pass_fail_status},
        )

        self._session.commit()
        self._session.refresh(ev)
        return PaperValidationEvidenceResponse.model_validate(ev)

    def include_evidence(self, plan_id: str, evidence_id: str) -> PaperValidationEvidenceResponse:
        plan = self._load_plan(plan_id)
        ev = self._load_evidence(plan_id, evidence_id)
        ev.included_in_metrics = True

        self._add_event(
            plan.id,
            "evidence_included",
            f"Evidence {evidence_id[:8]} included in metrics.",
        )
        computed = self._recalculate_in_place(plan)
        self._add_event(
            plan.id,
            "metrics_recalculated",
            "Metrics recalculated after evidence inclusion.",
            payload={"pass_fail_status": computed.pass_fail_status},
        )

        self._session.commit()
        self._session.refresh(ev)
        return PaperValidationEvidenceResponse.model_validate(ev)

    def reconcile(
        self,
        plan_id: str,
        body: PaperValidationReconcileRequest,
    ) -> PaperValidationReconcileResponse:
        """Scan signal_outcomes and ingest matching records as evidence.

        Matching strategy (low confidence — no direct strategy_config link on signals):
          - asset.symbol = candidate.asset (or body.asset_filter if provided)
          - signal.timeframe = candidate.timeframe (or body.timeframe_filter if provided)
          - signal_outcome.closed_at >= plan.started_at (or body.date_from if provided)
          - Deduplicate by source_type='signal_outcome' + source_id

        This only reads existing records. No trades are created or placed.
        Live trading status is not affected.
        """
        plan = self._load_plan(plan_id)
        warnings: list[str] = []

        # Load baseline_candidate for asset/timeframe
        candidate: BaselineCandidate | None = None
        if plan.baseline_candidate_id:
            candidate = self._session.get(BaselineCandidate, plan.baseline_candidate_id)
        if candidate is None:
            warnings.append("Baseline candidate not found — using asset/timeframe filters only.")

        asset_filter = body.asset_filter or (candidate.asset if candidate else None)
        timeframe_filter = body.timeframe_filter or (candidate.timeframe if candidate else None)
        date_from = body.date_from or plan.started_at
        date_to = body.date_to

        if not asset_filter:
            warnings.append(
                "No asset filter and no baseline candidate — reconciliation will match all assets (low precision)."
            )

        # Build query: signal_outcomes → signals (timeframe) → assets (symbol)
        stmt = (
            select(SignalOutcome)
            .join(Signal, Signal.id == SignalOutcome.signal_id)
            .join(Asset, Asset.id == SignalOutcome.asset_id)
            .where(SignalOutcome.closed_at.isnot(None))
        )
        if asset_filter:
            stmt = stmt.where(Asset.symbol == asset_filter)
        if timeframe_filter:
            stmt = stmt.where(Signal.timeframe == timeframe_filter)
        if date_from:
            stmt = stmt.where(SignalOutcome.closed_at >= date_from)
        if date_to:
            stmt = stmt.where(SignalOutcome.closed_at <= date_to)

        signal_outcomes = list(self._session.execute(stmt).scalars().all())

        if not signal_outcomes:
            warnings.append(
                "No signal_outcome records found matching the filter. "
                "Manual evidence ingestion is available via POST /evidence/manual."
            )

        # Load existing evidence source IDs to dedup
        existing_source_ids: set[uuid.UUID] = set(
            row
            for row in self._session.execute(
                select(PaperValidationEvidence.source_id).where(
                    and_(
                        PaperValidationEvidence.paper_validation_plan_id == plan.id,
                        PaperValidationEvidence.source_type == "signal_outcome",
                        PaperValidationEvidence.source_id.isnot(None),
                    )
                )
            ).scalars().all()
            if row is not None
        )

        created = 0
        skipped = 0

        for so in signal_outcomes:
            if so.id in existing_source_ids:
                skipped += 1
                continue

            # Classify result from predicted_direction_correct + pnl
            result = "unknown"
            pnl = _to_float(so.actual_pnl_pct)
            if pnl is not None:
                if pnl > 0.001:
                    result = "win"
                elif pnl < -0.001:
                    result = "loss"
                else:
                    result = "breakeven"
            elif so.predicted_direction_correct is True:
                result = "win"
            elif so.predicted_direction_correct is False:
                result = "loss"

            if not body.dry_run:
                ev = PaperValidationEvidence(
                    paper_validation_plan_id=plan.id,
                    source_type="signal_outcome",
                    source_id=so.id,
                    confidence="low",
                    asset=asset_filter,
                    timeframe=timeframe_filter,
                    side=None,
                    opened_at=None,
                    closed_at=so.closed_at,
                    entry_price=_to_float(so.entry_price),
                    exit_price=_to_float(so.exit_price),
                    pnl_amount=None,
                    pnl_pct=pnl,
                    r_multiple=_to_float(so.r_multiple),
                    result=result,
                    payload={"signal_id": str(so.signal_id)},
                    included_in_metrics=True,
                )
                self._session.add(ev)
            created += 1

        if not body.dry_run and created > 0:
            self._add_event(
                plan.id,
                "reconciled",
                f"Reconciled {created} signal_outcome records into evidence.",
                payload={
                    "created": created,
                    "skipped": skipped,
                    "asset_filter": asset_filter,
                    "timeframe_filter": timeframe_filter,
                    "warnings": warnings,
                },
            )
            computed = self._recalculate_in_place(plan)
            self._add_event(
                plan.id,
                "metrics_recalculated",
                "Metrics recalculated after reconciliation.",
                payload={"pass_fail_status": computed.pass_fail_status},
            )
            self._session.commit()
        elif not body.dry_run:
            self._session.commit()

        if not asset_filter and not timeframe_filter:
            warnings.append(
                "Matched with no asset/timeframe filter. Confidence is low. "
                "Provide asset_filter and timeframe_filter for higher precision."
            )

        return PaperValidationReconcileResponse(
            evidence_created=created,
            evidence_skipped=skipped,
            matched_source="signal_outcomes",
            warnings=warnings,
            dry_run=body.dry_run,
        )

    def get_dashboard_summary(self) -> "PaperValidationDashboardResponse":
        """Get dashboard summary for all paper validation plans."""
        from app.schemas.strategy_lab import PaperValidationDashboardResponse

        plans = list(self._session.execute(select(PaperValidationPlan)).scalars().all())

        counts = {
            "pending": sum(1 for p in plans if p.status == "pending"),
            "active": sum(1 for p in plans if p.status == "active"),
            "passed": sum(1 for p in plans if p.status == "passed"),
            "failed": sum(1 for p in plans if p.status == "failed"),
            "stopped": sum(1 for p in plans if p.status == "stopped"),
        }

        # Calculate ready_for_review count
        ready_count = 0
        for plan in plans:
            if plan.status == "active":
                progress = self._compute_progress(plan)
                if (
                    progress.progress_trades_pct >= 100
                    and progress.progress_days_pct >= 100
                ):
                    ready_count += 1

        # Calculate average progress
        active_plans = [p for p in plans if p.status == "active"]
        if active_plans:
            avg_trades = sum(
                _to_float(self._compute_progress(p).progress_trades_pct) or 0
                for p in active_plans
            ) / len(active_plans)
            avg_days = sum(
                _to_float(self._compute_progress(p).progress_days_pct) or 0
                for p in active_plans
            ) / len(active_plans)
        else:
            avg_trades = 0.0
            avg_days = 0.0

        # Plans needing evidence
        plans_needing_evidence = 0
        plans_with_low_confidence = 0
        plans_breaching_thresholds = 0

        for plan in plans:
            evidence_rows = list(
                self._session.execute(
                    select(PaperValidationEvidence).where(
                        PaperValidationEvidence.paper_validation_plan_id == plan.id
                    )
                ).scalars().all()
            )

            if not evidence_rows:
                plans_needing_evidence += 1

            # Count low confidence
            low_conf = sum(1 for e in evidence_rows if e.confidence == "low")
            if low_conf > 0 and len(evidence_rows) > 0:
                if low_conf / len(evidence_rows) >= 0.5:
                    plans_with_low_confidence += 1

            # Check thresholds
            if plan.status == "active":
                progress = self._compute_progress(plan)
                breached = False
                if (
                    plan.max_drawdown_pct is not None
                    and progress.max_drawdown_pct is not None
                    and progress.max_drawdown_pct > plan.max_drawdown_pct
                ):
                    breached = True
                if (
                    plan.target_profit_factor is not None
                    and progress.profit_factor is not None
                    and progress.profit_factor < plan.target_profit_factor
                ):
                    breached = True
                if breached:
                    plans_breaching_thresholds += 1

        # Recently updated (last 5)
        recently_updated = sorted(
            plans, key=lambda p: p.updated_at, reverse=True
        )[:5]
        recently_updated_items = [
            {
                "plan_id": str(p.id),
                "status": p.status,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in recently_updated
        ]

        warnings: list[str] = []
        if plans_breaching_thresholds > 0:
            warnings.append(
                f"{plans_breaching_thresholds} plan(s) are breaching risk thresholds."
            )
        if plans_with_low_confidence > 0:
            warnings.append(
                f"{plans_with_low_confidence} plan(s) have high ratio of low-confidence evidence."
            )

        return PaperValidationDashboardResponse(
            total_plans=len(plans),
            pending_count=counts["pending"],
            active_count=counts["active"],
            passed_count=counts["passed"],
            failed_count=counts["failed"],
            stopped_count=counts["stopped"],
            ready_for_review_count=ready_count,
            average_progress_trades_pct=float(avg_trades),
            average_progress_days_pct=float(avg_days),
            plans_needing_evidence=plans_needing_evidence,
            plans_with_low_confidence=plans_with_low_confidence,
            plans_breaching_thresholds=plans_breaching_thresholds,
            recently_updated_plans=recently_updated_items,
            warnings=warnings,
        )

    def get_readiness_review(self, plan_id: str) -> "PaperValidationReadinessResponse":
        """Get readiness review for a single paper validation plan."""
        from app.schemas.strategy_lab import (
            PaperValidationEvidenceSummary,
            PaperValidationMetricDeltas,
            PaperValidationReadinessResponse,
        )

        plan = self._load_plan(plan_id)

        # Compute progress
        progress = self._compute_progress(plan)

        # Determine readiness_status
        readiness_status = "not_started"
        if plan.status == "passed":
            readiness_status = "passed"
        elif plan.status == "failed":
            readiness_status = "failed"
        elif plan.status == "stopped":
            readiness_status = "stopped"
        elif plan.status == "active":
            if (
                progress.progress_trades_pct >= 100
                and progress.progress_days_pct >= 100
            ):
                readiness_status = "ready_for_review"
            else:
                readiness_status = "collecting_evidence"

        # Calculate readiness_score (0-100)
        score = 0

        # Trade progress (0-25)
        trade_pct = _to_float(progress.progress_trades_pct) or 0
        score += int(min(25, (trade_pct / 100) * 25))

        # Days progress (0-20)
        days_pct = _to_float(progress.progress_days_pct) or 0
        score += int(min(20, (days_pct / 100) * 20))

        # Profit factor (0-20)
        if plan.target_profit_factor is not None and progress.profit_factor is not None:
            pf_ratio = progress.profit_factor / plan.target_profit_factor
            score += int(min(20, max(0, pf_ratio * 20)))

        # Drawdown (0-15)
        if (
            plan.max_drawdown_pct is not None
            and progress.max_drawdown_pct is not None
        ):
            dd_ratio = 1 - (progress.max_drawdown_pct / plan.max_drawdown_pct)
            score += int(min(15, max(0, dd_ratio * 15)))

        # Evidence confidence (0-10)
        evidence_rows = list(
            self._session.execute(
                select(PaperValidationEvidence).where(
                    PaperValidationEvidence.paper_validation_plan_id == plan.id
                )
            ).scalars().all()
        )
        if evidence_rows:
            high = sum(1 for e in evidence_rows if e.confidence == "high")
            medium = sum(1 for e in evidence_rows if e.confidence == "medium")
            confidence_ratio = (high * 1.0 + medium * 0.5) / len(evidence_rows)
            score += int(min(10, confidence_ratio * 10))

        # Paper vs backtest consistency (0-10)
        if (
            plan.backtest_metrics
            and plan.paper_metrics
            and progress.profit_factor is not None
        ):
            backtest_pf = _to_float(plan.backtest_metrics.get("profit_factor"))
            if backtest_pf is not None and backtest_pf > 0:
                consistency = progress.profit_factor / backtest_pf
                # +10 if within 20% of backtest, -10 if >50% worse
                if consistency >= 0.8:
                    score += 10
                elif consistency >= 0.5:
                    score += 5
                # else penalize (already counted negatively above)

        score = max(0, min(100, score))

        # If plan failed, cap score
        if plan.status == "failed":
            score = min(20, score)

        # Calculate metric deltas
        deltas = PaperValidationMetricDeltas()
        if plan.backtest_metrics and plan.paper_metrics:
            backtest_pf = _to_float(plan.backtest_metrics.get("profit_factor"))
            paper_pf = progress.profit_factor
            if backtest_pf is not None and paper_pf is not None:
                deltas.profit_factor_delta = paper_pf - backtest_pf

            backtest_ret = _to_float(plan.backtest_metrics.get("total_return_pct"))
            paper_ret = _to_float(plan.paper_metrics.get("total_return_pct"))
            if backtest_ret is not None and paper_ret is not None:
                deltas.total_return_delta = paper_ret - backtest_ret

            backtest_dd = _to_float(plan.backtest_metrics.get("max_drawdown_pct"))
            paper_dd = progress.max_drawdown_pct
            if backtest_dd is not None and paper_dd is not None:
                deltas.max_drawdown_delta = paper_dd - backtest_dd

            backtest_wr = _to_float(plan.backtest_metrics.get("win_rate"))
            paper_wr = progress.win_rate
            if backtest_wr is not None and paper_wr is not None:
                deltas.win_rate_delta = paper_wr - backtest_wr

        # Evidence summary
        high = sum(1 for e in evidence_rows if e.confidence == "high")
        medium = sum(1 for e in evidence_rows if e.confidence == "medium")
        low = sum(1 for e in evidence_rows if e.confidence == "low")
        manual = sum(1 for e in evidence_rows if e.source_type == "manual")
        reconciled = sum(1 for e in evidence_rows if e.source_type == "signal_outcome")
        included = sum(1 for e in evidence_rows if e.included_in_metrics)
        excluded = len(evidence_rows) - included

        evidence_summary = PaperValidationEvidenceSummary(
            total_evidence=len(evidence_rows),
            included_evidence=included,
            excluded_evidence=excluded,
            manual_evidence_count=manual,
            reconciled_evidence_count=reconciled,
            high_confidence_count=high,
            medium_confidence_count=medium,
            low_confidence_count=low,
        )

        # Warnings
        warnings: list[str] = []
        if progress.progress_trades_pct < 100:
            warnings.append(
                f"Not enough trades yet: {progress.progress_trades_pct:.0f}% of {plan.required_trades} required."
            )
        if progress.progress_days_pct < 100:
            warnings.append(
                f"Not enough days yet: {progress.progress_days_pct:.0f}% of {plan.minimum_days} required."
            )
        if (
            plan.target_profit_factor is not None
            and progress.profit_factor is not None
            and progress.profit_factor < plan.target_profit_factor
        ):
            warnings.append(
                f"Profit factor below target: {progress.profit_factor:.2f} < {plan.target_profit_factor:.2f}."
            )
        if (
            plan.max_drawdown_pct is not None
            and progress.max_drawdown_pct is not None
            and progress.max_drawdown_pct > plan.max_drawdown_pct
        ):
            warnings.append(
                f"Max drawdown exceeded: {progress.max_drawdown_pct:.2f}% > {plan.max_drawdown_pct:.2f}%."
            )
        if len(evidence_rows) > 0 and low > 0:
            if low / len(evidence_rows) >= 0.5:
                warnings.append(
                    f"High ratio of low-confidence evidence: {low}/{len(evidence_rows)}."
                )
        if len(evidence_rows) > 0 and manual > 0:
            if manual / len(evidence_rows) >= 0.5:
                warnings.append(
                    f"High ratio of manual evidence: {manual}/{len(evidence_rows)}. Consider more reconciliation."
                )

        # Paper vs backtest consistency warning
        if plan.backtest_metrics and progress.profit_factor is not None:
            backtest_pf = _to_float(plan.backtest_metrics.get("profit_factor"))
            if backtest_pf is not None and backtest_pf > 0:
                consistency = progress.profit_factor / backtest_pf
                if consistency < 0.5:
                    warnings.append(
                        f"Paper results significantly worse than backtest: {(consistency * 100):.0f}% of backtest profit factor."
                    )

        # Suggested next action
        suggested_next_action = "keep_collecting"
        if plan.status == "passed":
            suggested_next_action = "review_candidate"
        elif plan.status == "failed":
            suggested_next_action = "reject_candidate"
        elif plan.status == "stopped":
            suggested_next_action = "investigate_data"
        elif readiness_status == "ready_for_review":
            if len(warnings) > 3:
                suggested_next_action = "investigate_data"
            else:
                suggested_next_action = "review_candidate"
        elif not evidence_rows:
            suggested_next_action = "keep_collecting"
        elif (
            low > 0
            and len(evidence_rows) > 0
            and low / len(evidence_rows) >= 0.75
        ):
            suggested_next_action = "investigate_data"

        # Recent events
        events = list(
            self._session.execute(
                select(PaperValidationEvent)
                .where(PaperValidationEvent.paper_validation_plan_id == plan.id)
                .order_by(PaperValidationEvent.created_at.desc())
                .limit(10)
            ).scalars().all()
        )
        event_responses = [
            PaperValidationEventResponse(
                id=str(e.id),
                event_type=e.event_type,
                message=e.message,
                payload=e.payload or {},
                created_at=e.created_at,
            )
            for e in events
        ]

        readiness_notes = ""
        if plan.status == "failed":
            readiness_notes = "This plan has failed validation. Consider stopping or investigating."
        elif readiness_status == "collecting_evidence":
            readiness_notes = (
                "Collecting evidence. Once requirements are met, readiness will be re-evaluated."
            )
        elif readiness_status == "ready_for_review":
            readiness_notes = (
                "This plan meets minimum requirements and is ready for operator review."
            )

        return PaperValidationReadinessResponse(
            plan_id=plan.id,
            baseline_candidate_id=plan.baseline_candidate_id,
            status=plan.status,
            readiness_status=readiness_status,
            readiness_score=score,
            readiness_notes=readiness_notes,
            progress_summary={
                "progress_trades_pct": progress.progress_trades_pct,
                "progress_days_pct": progress.progress_days_pct,
                "total_paper_trades": progress.total_paper_trades,
                "losses": progress.losses,
                "wins": progress.wins,
                "days_active": progress.days_active,
            },
            backtest_metrics=plan.backtest_metrics,
            paper_metrics=plan.paper_metrics,
            metric_deltas=deltas,
            evidence_summary=evidence_summary,
            warnings=warnings,
            suggested_next_action=suggested_next_action,
            recent_events=event_responses,
        )
