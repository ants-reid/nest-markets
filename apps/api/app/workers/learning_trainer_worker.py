"""LearningTrainerWorker — create scoring model candidates from live outcomes.

This worker does not auto-promote models. It periodically snapshots live
signal outcome performance into the score model registry as new CANDIDATE
versions for later governance/promotion review.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, inspect, select

from app.config import get_settings
from app.db.enums import HorizonLabel, ModelRegistryStatus, SignalStatus, TradeDirection
from app.db.models.bar import Bar
from app.db.models.signal import Signal
from app.db.models.score_model_evaluations import ScoreModelEvaluation
from app.db.models.score_model_registry import ScoreModelRegistry
from app.db.models.signal_outcome import SignalOutcome
from app.db.session import SessionLocal
from app.services.performance_stats_service import PerformanceStatsService
from app.workers.base_worker import BaseWorker

_logger = logging.getLogger(__name__)


class LearningTrainerWorker(BaseWorker):
    """Periodically register a new candidate model version from live outcomes."""

    worker_name = "learning_trainer"
    _BUCKET = "auto_paper"
    _ASSET_CLASS = "equity"
    _COUNTERFACTUAL_LOOKBACK_DAYS = 45
    _COUNTERFACTUAL_MAX_SIGNALS = 300

    @staticmethod
    def _horizon_delta(horizon: HorizonLabel | None) -> timedelta:
        if horizon == HorizonLabel.INTRADAY:
            return timedelta(hours=8)
        if horizon == HorizonLabel.ONE_TO_THREE_DAYS:
            return timedelta(days=2)
        if horizon == HorizonLabel.THREE_TO_TEN_DAYS:
            return timedelta(days=7)
        return timedelta(days=2)

    def _counterfactual_stats(self, session, *, now_utc: datetime) -> dict[str, object]:
        """Estimate missed-signal directional accuracy from matured candidate signals."""
        lookback_cutoff = now_utc - timedelta(days=self._COUNTERFACTUAL_LOOKBACK_DAYS)

        no_outcome_exists = (
            select(SignalOutcome.id)
            .where(SignalOutcome.signal_id == Signal.id)
            .exists()
        )

        signals_stmt = (
            select(Signal)
            .where(
                Signal.scan_ts >= lookback_cutoff,
                Signal.signal_status.in_(
                    [
                        SignalStatus.CANDIDATE,
                        SignalStatus.RISK_BLOCKED,
                        SignalStatus.USER_REJECTED,
                        SignalStatus.EXPIRED,
                    ]
                ),
                ~no_outcome_exists,
            )
            .order_by(Signal.scan_ts.desc())
            .limit(self._COUNTERFACTUAL_MAX_SIGNALS)
        )
        candidate_signals = list(session.execute(signals_stmt).scalars().all())

        evaluated = 0
        wins = 0
        by_setup: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "wins": 0})

        for signal in candidate_signals:
            horizon_delta = self._horizon_delta(signal.horizon_label)
            expiry_ts = signal.scan_ts + horizon_delta
            if now_utc < expiry_ts:
                continue

            entry_stmt = (
                select(Bar.close)
                .where(
                    Bar.asset_id == signal.asset_id,
                    Bar.timeframe == signal.timeframe,
                    Bar.ts >= signal.scan_ts,
                )
                .order_by(Bar.ts.asc())
                .limit(1)
            )
            exit_stmt = (
                select(Bar.close)
                .where(
                    Bar.asset_id == signal.asset_id,
                    Bar.timeframe == signal.timeframe,
                    Bar.ts >= expiry_ts,
                )
                .order_by(Bar.ts.asc())
                .limit(1)
            )

            entry_px = session.execute(entry_stmt).scalar_one_or_none()
            exit_px = session.execute(exit_stmt).scalar_one_or_none()
            if entry_px is None or exit_px is None:
                continue

            entry = float(entry_px)
            exit_ = float(exit_px)
            if entry <= 0:
                continue

            correct = False
            if signal.direction == TradeDirection.LONG:
                correct = exit_ > entry
            elif signal.direction == TradeDirection.SHORT:
                correct = exit_ < entry
            else:
                continue

            evaluated += 1
            if correct:
                wins += 1

            setup_key = signal.setup_type.value if signal.setup_type else "unknown"
            by_setup[setup_key]["total"] += 1
            if correct:
                by_setup[setup_key]["wins"] += 1

        by_setup_rows = []
        for setup, row in by_setup.items():
            total = int(row["total"])
            if total <= 0:
                continue
            setup_wins = int(row["wins"])
            by_setup_rows.append(
                {
                    "setup": setup,
                    "total": total,
                    "wins": setup_wins,
                    "win_rate": round(setup_wins / total, 4),
                }
            )

        by_setup_rows.sort(key=lambda r: r["win_rate"], reverse=True)
        overall = round((wins / evaluated), 4) if evaluated > 0 else 0.0
        return {
            "total": evaluated,
            "wins": wins,
            "win_rate": overall,
            "by_setup": by_setup_rows[:12],
            "lookback_days": self._COUNTERFACTUAL_LOOKBACK_DAYS,
        }

    def execute(self) -> str:
        settings = get_settings()
        if not settings.auto_learning_enabled:
            return "learning_trainer: skipped (AUTO_LEARNING_ENABLED=false)"

        session = SessionLocal()
        try:
            inspector = inspect(session.bind)
            required_tables = {"score_model_registry", "score_model_evaluations", "signal_outcomes", "signals", "bars"}
            missing_tables = [t for t in required_tables if not inspector.has_table(t)]
            if missing_tables:
                return (
                    "learning_trainer: skipped (missing tables; run migrations) "
                    f"missing={','.join(sorted(missing_tables))}"
                )

            latest_stmt = (
                select(ScoreModelRegistry)
                .where(
                    ScoreModelRegistry.strategy_bucket == self._BUCKET,
                    ScoreModelRegistry.asset_class == self._ASSET_CLASS,
                )
                .order_by(
                    ScoreModelRegistry.version_number.desc(),
                    ScoreModelRegistry.training_date.desc(),
                )
                .limit(1)
            )
            latest = session.execute(latest_stmt).scalars().first()

            min_hours = max(1, int(settings.auto_learning_min_hours_between_versions))
            now_utc = datetime.now(UTC)
            if latest is not None and latest.training_date is not None:
                if now_utc - latest.training_date < timedelta(hours=min_hours):
                    return (
                        "learning_trainer: skipped (cooldown active; "
                        f"last_version={latest.version_number})"
                    )

            stats = PerformanceStatsService(session).overall_stats(min_samples=1)
            total = int(stats.total_trades)

            since_dt = latest.training_date if latest is not None else None
            if since_dt is not None:
                new_outcomes_stmt = select(func.count()).where(
                    SignalOutcome.predicted_direction_correct.is_not(None),
                    SignalOutcome.created_at > since_dt,
                )
                new_outcomes = int(session.execute(new_outcomes_stmt).scalar_one() or 0)
            else:
                new_outcomes = total

            counterfactual = self._counterfactual_stats(session, now_utc=now_utc)
            effective_total_samples = int(total + int(counterfactual["total"]))
            min_total = max(1, int(settings.auto_learning_min_total_outcomes))
            if effective_total_samples < min_total:
                return (
                    "learning_trainer: skipped (insufficient total samples; "
                    f"have={effective_total_samples} need={min_total})"
                )

            effective_new_samples = int(new_outcomes + int(counterfactual["total"]))

            min_new = max(1, int(settings.auto_learning_min_new_outcomes))
            if effective_new_samples < min_new:
                return (
                    "learning_trainer: skipped (not enough new samples since last version; "
                    f"have={effective_new_samples} need={min_new})"
                )

            next_version = (latest.version_number + 1) if latest is not None else 1
            training_ts = now_utc
            model = ScoreModelRegistry(
                name=f"scoring-auto-v{next_version}",
                version_number=next_version,
                strategy_bucket=self._BUCKET,
                asset_class=self._ASSET_CLASS,
                description=(
                    "Auto-generated candidate from live outcomes and missed-signal counterfactuals. "
                    "Requires governance promotion before activation."
                ),
                training_date=training_ts,
                trained_by="learning_trainer_worker",
                status=ModelRegistryStatus.CANDIDATE,
                is_active=False,
            )
            session.add(model)
            session.flush()

            run_id = f"learning-trainer-{training_ts.strftime('%Y%m%d%H%M%S')}"
            eval_rows = [
                ("overall_win_rate", float(stats.overall_win_rate)),
                ("total_outcomes", float(total)),
                ("effective_total_samples", float(effective_total_samples)),
                ("new_outcomes_since_last", float(new_outcomes)),
                ("counterfactual_win_rate", float(counterfactual["win_rate"])),
                ("counterfactual_total", float(counterfactual["total"])),
                ("effective_new_samples_since_last", float(effective_new_samples)),
            ]
            for metric_name, metric_value in eval_rows:
                session.add(
                    ScoreModelEvaluation(
                        model_registry_id=model.id,
                        evaluation_run_id=run_id,
                        evaluation_date=training_ts,
                        validation_strategy="live_outcome_snapshot",
                        metric_name=metric_name,
                        metric_value=metric_value,
                        metric_details={
                            "by_setup": [
                                {
                                    "setup": row.key,
                                    "total": row.total,
                                    "wins": row.wins,
                                    "win_rate": row.win_rate,
                                }
                                for row in stats.by_setup[:12]
                            ],
                            "counterfactual": {
                                "total": counterfactual["total"],
                                "wins": counterfactual["wins"],
                                "win_rate": counterfactual["win_rate"],
                                "by_setup": counterfactual["by_setup"],
                                "lookback_days": counterfactual["lookback_days"],
                            },
                            "source": "signal_outcomes_plus_missed_counterfactual",
                        },
                        passed_gates=True,
                        gate_failures=[],
                        evaluated_by="learning_trainer_worker",
                    )
                )

            session.commit()
            return (
                "learning_trainer: candidate_registered "
                f"version={next_version} outcomes={total} new_outcomes={new_outcomes} "
                f"counterfactual={counterfactual['total']} effective_new={effective_new_samples} "
                f"win_rate={stats.overall_win_rate:.4f}"
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            _logger.error("learning_trainer fatal error: %s", exc)
            return f"learning_trainer: fatal error - {exc}"
        finally:
            session.close()
