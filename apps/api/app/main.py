from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes.approvals import router as approvals_router
from app.api.routes.asset_cards import router as asset_cards_router
from app.api.routes.assets import router as assets_router
from app.api.routes.broker import router as broker_router
from app.api.routes.broker_submit_decisions import router as broker_submit_decisions_router
from app.api.routes.news_in_decision_log import router as news_in_decision_log_router
from app.api.routes.evals import router as evals_router
from app.api.routes.governance import router as governance_router
from app.api.routes.models import router as models_router
from app.api.routes.opportunities import router as opportunities_router
from app.api.routes.options import router as options_router
from app.api.routes.performance import router as performance_router
from app.api.routes.prompt_adaptations import router as prompt_adaptations_router
from app.api.routes.execution import router as execution_router
from app.api.routes.health import router as health_router
from app.api.routes.llm_logs import router as llm_logs_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.markets import router as markets_router
from app.api.routes.monitor_feeds import router as monitor_feeds_router
from app.api.routes.monitor_health_history import router as monitor_health_history_router
from app.api.routes.monitor_test import router as monitor_test_router
from app.api.routes.monitor_worker_run_log import router as monitor_worker_run_log_router
from app.api.routes.cockpit_notifications import router as cockpit_notifications_router
from app.api.routes.cockpit_auto_paper_status import router as cockpit_auto_paper_status_router
from app.api.routes.cockpit_eod_report import router as cockpit_eod_report_router
from app.api.routes.cockpit_in_flight_adjustments import router as cockpit_in_flight_adjustments_router
from app.api.routes.cockpit_mode import router as cockpit_mode_router
from app.api.routes.monitor_incidents import router as monitor_incidents_router
from app.api.routes.news_articles import router as news_articles_router
from app.api.routes.prompts import router as prompts_router
from app.api.routes.regime import router as regime_router
from app.api.routes.risk import router as risk_router
from app.api.routes.risk_decisions import router as risk_decisions_router
from app.api.routes.risk_limits import router as risk_limits_router
from app.api.routes.trading_halt import router as trading_halt_router
from app.api.routes.research_jobs import router as research_jobs_router
from app.api.routes.baseline_candidates import router as baseline_candidates_router
from app.api.routes.paper_validation import router as paper_validation_router
from app.api.routes.paper_recommendations import router as paper_recommendations_router
from app.api.routes.strategy_lab import router as strategy_lab_router
from app.api.routes.scoring import router as scoring_router
from app.api.routes.research_data import router as research_data_router
from app.api.routes.signals import router as signals_router
from app.api.routes.workflow import router as workflow_router
from app.config import get_settings
from app.logging import configure_logging
from app.schedules.data_sync_scheduler import DataSyncScheduler
from app.services.prompt_version_service import seed_prompt_versions
from app.services.pnl_snapshot_worker import PnlSnapshotWorker
from app.services.worker_run_log_service import WorkerRunLogService, build_auto_paper_run_entry

_logger = logging.getLogger(__name__)


def _run_scheduled_auto_paper_job(worker, run_log: WorkerRunLogService | None = None) -> None:
    """Execute the scheduled auto-paper worker and persist a structured run-log entry."""
    result = worker.run()
    (run_log or WorkerRunLogService()).append(build_auto_paper_run_entry(result, source="scheduled"))


def _register_pnl_snapshot_scheduler(
    scheduler: AsyncIOScheduler,
    *,
    enabled: bool,
    interval_seconds: int,
) -> None:
    """Register scheduled active-account pnl snapshot capture (MH-46B-1)."""
    if not enabled:
        _logger.info("P&L snapshot scheduler disabled")
        return

    interval = max(15, int(interval_seconds))
    worker = PnlSnapshotWorker(min_interval_seconds=interval)

    async def _scheduled_capture() -> None:
        try:
            data = await worker.capture_once()
            mode = (data.get("broker_mode") or {}).get("mode")
            _logger.info(
                "Scheduled P&L snapshot captured: source=%s account_id=%s mode=%s ts=%s positions=%s",
                data.get("source"),
                data.get("account_id"),
                mode,
                data.get("snapshot_ts"),
                data.get("position_count"),
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Scheduled P&L snapshot capture failed: %s", exc)

    scheduler.add_job(
        _scheduled_capture,
        IntervalTrigger(seconds=interval),
        id="pnl_snapshot_capture",
        replace_existing=True,
    )
    _logger.info("P&L snapshot scheduler registered (every %ss)", interval)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start APScheduler on startup; stop cleanly on shutdown.

    The scheduler is deliberately disabled when ``APP_ENV=test`` to prevent
    background jobs from interfering with the pytest process.
    """
    scheduler: AsyncIOScheduler | None = None
    if os.getenv("APP_ENV", "development") != "test":
        settings = get_settings()
        # Seed prompt versions from disk
        from app.db.session import SessionLocal as _SessionLocal
        _seed_session = _SessionLocal()
        try:
            seed_prompt_versions(_seed_session)
            _seed_session.commit()
            _logger.info("Prompt versions seeded")
        except Exception as exc:
            _seed_session.rollback()
            _logger.warning("Prompt version seeding failed: %s", exc)
        finally:
            _seed_session.close()

        scheduler = AsyncIOScheduler()
        data_sync = DataSyncScheduler()
        auto_paper_run_log = WorkerRunLogService()
        for job in data_sync.list_jobs():
            if job.enabled:
                # signal_sweep runs on a short interval rather than its default cron
                if job.name == "signal_sweep":
                    scheduler.add_job(
                        data_sync.get_worker(job.name).run,
                        IntervalTrigger(seconds=30),
                        id=job.name,
                        replace_existing=True,
                    )
                    _logger.info("Scheduled job registered: %s (every 30s)", job.name)
                elif job.name == "auto_paper_trader":
                    worker = data_sync.get_worker(job.name)
                    scheduler.add_job(
                        lambda worker=worker, run_log=auto_paper_run_log: _run_scheduled_auto_paper_job(worker, run_log),
                        CronTrigger.from_crontab(job.cron),
                        id=job.name,
                        replace_existing=True,
                    )
                    _logger.info("Scheduled job registered: %s (%s)", job.name, job.cron)
                else:
                    scheduler.add_job(
                        data_sync.get_worker(job.name).run,
                        CronTrigger.from_crontab(job.cron),
                        id=job.name,
                        replace_existing=True,
                    )
                    _logger.info("Scheduled job registered: %s (%s)", job.name, job.cron)
        scheduler.start()
        app.state.scheduler = scheduler
        _logger.info("APScheduler started")

        # Emit paper mode status at startup so operators can confirm safety posture
        from app.services.broker_mode_guard import get_broker_mode_metadata
        _bm = get_broker_mode_metadata()
        _logger.info(
            "BROKER MODE: provider=%s mode=%s live_execution_enabled=%s paper_trading_enabled=%s",
            _bm["broker"],
            _bm["mode"],
            _bm["live_execution_enabled"],
            _bm["paper_trading_enabled"],
        )
        if _bm["live_execution_enabled"] or not _bm["paper_trading_enabled"]:
            _logger.error(
                "BROKER SAFETY WARNING: live execution configuration detected at startup! "
                "Check LIVE_EXECUTION_ENABLED, BROKER_MODE, IBKR_ACCOUNT_TYPE."
            )

        # Broker gateway keep-alive: POST /tickle every 55 s to prevent session expiry
        async def _broker_tickle() -> None:
            try:
                from app.api.routes.broker import get_broker_service
                svc = get_broker_service()
                if svc._broker and svc._broker.is_connected:
                    await svc._broker.tickle()
            except Exception as exc:  # noqa: BLE001
                _logger.debug("Broker tickle failed (session may be expired): %s", exc)

        scheduler.add_job(
            _broker_tickle,
            IntervalTrigger(seconds=55),
            id="broker_tickle",
            replace_existing=True,
        )
        _logger.info("Broker tickle job registered (every 55s)")

        _register_pnl_snapshot_scheduler(
            scheduler,
            enabled=settings.pnl_snapshot_scheduler_enabled,
            interval_seconds=settings.pnl_snapshot_interval_seconds,
        )

    yield

    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        _logger.info("APScheduler stopped")


# Global rate limiter — 200 requests/minute per IP
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=_lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_origin_regex=settings.cors_allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID"],
    )

    # MH-160 — Correlation ID plumbing. Passive middleware: assigns/echoes a
    # request-scoped correlation id; never alters status codes or bodies.
    from app.services.correlation_context import CorrelationIDMiddleware

    app.add_middleware(CorrelationIDMiddleware)

    app.include_router(health_router)
    app.include_router(llm_logs_router)
    app.include_router(news_articles_router)
    app.include_router(markets_router)
    app.include_router(asset_cards_router)
    app.include_router(monitor_incidents_router)
    app.include_router(monitor_feeds_router)
    app.include_router(monitor_health_history_router)
    app.include_router(monitor_test_router)
    app.include_router(monitor_worker_run_log_router)
    app.include_router(cockpit_notifications_router)
    app.include_router(cockpit_auto_paper_status_router)
    app.include_router(cockpit_eod_report_router)
    app.include_router(cockpit_in_flight_adjustments_router)
    app.include_router(cockpit_mode_router)
    app.include_router(assets_router)
    app.include_router(opportunities_router)
    app.include_router(signals_router)
    app.include_router(risk_router)
    app.include_router(risk_limits_router)
    app.include_router(trading_halt_router)
    app.include_router(approvals_router)
    app.include_router(execution_router)
    app.include_router(workflow_router)
    app.include_router(prompts_router)
    app.include_router(market_data_router)
    app.include_router(evals_router)
    app.include_router(performance_router)
    app.include_router(prompt_adaptations_router)
    app.include_router(scoring_router)
    app.include_router(models_router)
    app.include_router(governance_router)
    app.include_router(regime_router)
    app.include_router(broker_router)
    app.include_router(broker_submit_decisions_router)
    app.include_router(news_in_decision_log_router)
    app.include_router(risk_decisions_router)
    app.include_router(options_router)
    app.include_router(research_data_router)
    app.include_router(research_jobs_router)
    app.include_router(strategy_lab_router)
    app.include_router(baseline_candidates_router)
    app.include_router(paper_validation_router)
    app.include_router(paper_recommendations_router)

    return app


app = create_app()
