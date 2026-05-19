"""AIBacktestReportService — MH-14: generate LLM-powered research reports for backtest runs."""

from __future__ import annotations

import statistics
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.llm.base import LLMRequest
from app.clients.llm.router import LLMProviderRouter
from app.config import get_settings
from app.db.models.ai_backtest_report import AIBacktestReport
from app.db.models.backtest_run import BacktestRun
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.schemas.strategy_lab import (
    AIBacktestReportListResponse,
    AIBacktestReportRequest,
    AIBacktestReportResponse,
)

# ── AI output JSON schema ──────────────────────────────────────────────────

_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "plain_english_summary": {"type": "string"},
        "strongest_configs": {"type": "array", "items": {"type": "string"}},
        "weak_configs": {"type": "array", "items": {"type": "string"}},
        "overfitting_warnings": {"type": "array", "items": {"type": "string"}},
        "sample_size_warnings": {"type": "array", "items": {"type": "string"}},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
        "data_quality_notes": {"type": "array", "items": {"type": "string"}},
        "recommended_next_tests": {"type": "array", "items": {"type": "string"}},
        "reject_or_continue": {
            "type": "string",
            "enum": ["continue_testing", "needs_more_data", "reject_for_now"],
        },
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 100},
    },
    "required": [
        "plain_english_summary",
        "strongest_configs",
        "weak_configs",
        "overfitting_warnings",
        "sample_size_warnings",
        "risk_notes",
        "data_quality_notes",
        "recommended_next_tests",
        "reject_or_continue",
        "confidence_score",
    ],
}

_SYSTEM_PROMPT = """You are a quantitative research analyst reviewing systematic trading backtest results.
Your job is to critically evaluate a set of backtested strategy configurations and provide an honest,
structured research report. Be concise, specific, and data-driven. Flag any concerns about overfitting,
insufficient sample sizes, or unrealistic results. Your response must be valid JSON matching the provided schema."""


def _build_input_summary(
    run: BacktestRun,
    results: list[StrategyResult],
    focus: str,
    config_lookup: dict[str, StrategyConfig] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, LLM-friendly summary of the backtest run and its results."""
    sorted_results = sorted(
        results,
        key=lambda r: float(r.score or 0),
        reverse=True,
    )

    def _row(r: StrategyResult) -> dict[str, Any]:
        strategy_config_id = str(r.strategy_config_id) if r.strategy_config_id else None
        config = config_lookup.get(strategy_config_id) if (config_lookup and strategy_config_id) else None
        win_rate = float(r.win_rate) if r.win_rate is not None else None
        profit_factor = float(r.profit_factor) if r.profit_factor is not None else None
        total_return_pct = float(r.total_return_pct) if r.total_return_pct is not None else None
        max_drawdown_pct = float(r.max_drawdown_pct) if r.max_drawdown_pct is not None else None
        score = float(r.score) if r.score is not None else None

        return {
            "id": str(r.id),
            "strategy_config_id": strategy_config_id,
            "strategy_name": config.name if config else (f"Config {strategy_config_id[:8]}" if strategy_config_id else "Unknown config"),
            "parameters": dict(config.parameters) if config else {},
            "asset": r.asset,
            "timeframe": r.timeframe,
            "total_trades": r.total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_return_pct": total_return_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "score": score,
            "metrics": {
                "total_trades": r.total_trades,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_return_pct": total_return_pct,
                "max_drawdown_pct": max_drawdown_pct,
                "score": score,
            },
        }

    top_10 = [_row(r) for r in sorted_results[:10]]
    bottom_5 = [_row(r) for r in sorted_results[-5:]] if len(sorted_results) > 10 else []

    scores = [float(r.score) for r in results if r.score is not None]
    score_distribution: dict[str, Any] = {}
    if scores:
        score_distribution = {
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "mean": round(statistics.mean(scores), 2),
            "median": round(statistics.median(scores), 2),
        }

    trades = [r.total_trades for r in results]
    return_pcts = [float(r.total_return_pct) for r in results if r.total_return_pct is not None]
    drawdowns = [float(r.max_drawdown_pct) for r in results if r.max_drawdown_pct is not None]

    return {
        "run_name": run.name,
        "date_from": run.date_from.date().isoformat() if run.date_from else None,
        "date_to": run.date_to.date().isoformat() if run.date_to else None,
        "starting_capital": float(run.starting_capital or 10000),
        "requested_assets": run.requested_assets,
        "requested_timeframes": run.requested_timeframes,
        "config_count": len(results),
        "focus": focus,
        "score_distribution": score_distribution,
        "total_trades_stats": {
            "min": min(trades) if trades else 0,
            "max": max(trades) if trades else 0,
            "mean": round(statistics.mean(trades), 1) if trades else 0,
        },
        "return_pct_stats": {
            "min": round(min(return_pcts), 2) if return_pcts else None,
            "max": round(max(return_pcts), 2) if return_pcts else None,
            "mean": round(statistics.mean(return_pcts), 2) if return_pcts else None,
        },
        "drawdown_stats": {
            "min": round(min(drawdowns), 2) if drawdowns else None,
            "max": round(max(drawdowns), 2) if drawdowns else None,
            "mean": round(statistics.mean(drawdowns), 2) if drawdowns else None,
        },
        "top_10_configs": top_10,
        "bottom_5_configs": bottom_5,
    }


def _build_user_prompt(input_summary: dict[str, Any]) -> str:
    import json
    return (
        "Please review the following backtest run summary and produce a structured research report.\n\n"
        f"Focus area: {input_summary.get('focus', 'balanced')}\n\n"
        "## Backtest Summary\n"
        f"```json\n{json.dumps(input_summary, indent=2, default=str)}\n```\n\n"
        "Respond with a JSON object matching the schema. Be direct and specific. "
        "Mention config IDs or rank positions when referencing specific results."
    )


def _normalise_confidence_score(raw_score: Any) -> float | None:
    """Normalize confidence into a 0..100 scale for storage and UI display."""
    if raw_score is None:
        return None
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None

    if 0.0 <= score <= 1.0:
        score *= 100.0

    score = max(0.0, min(100.0, score))
    return round(score, 2)


def _build_config_index(input_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build a lookup of config details from top/bottom summary sections."""
    index: dict[str, dict[str, Any]] = {}
    for key in ("top_10_configs", "bottom_5_configs"):
        for row in input_summary.get(key, []) or []:
            if not isinstance(row, dict):
                continue
            cfg_id = row.get("strategy_config_id")
            if isinstance(cfg_id, str) and cfg_id:
                index[cfg_id] = row
    return index


def _normalise_config_items(
    values: Any,
    input_summary: dict[str, Any],
) -> list[Any]:
    """Convert config references to richer objects where possible, keeping fallback strings."""
    if not isinstance(values, list):
        return []

    config_index = _build_config_index(input_summary)
    normalized: list[Any] = []

    for value in values:
        if isinstance(value, dict):
            cfg_id = value.get("strategy_config_id")
            base = config_index.get(str(cfg_id)) if cfg_id else None
            metrics = value.get("metrics") if isinstance(value.get("metrics"), dict) else None
            parameters = value.get("parameters") if isinstance(value.get("parameters"), dict) else None
            normalized.append(
                {
                    "strategy_config_id": cfg_id,
                    "strategy_name": value.get("strategy_name") or (base.get("strategy_name") if base else "Unknown config"),
                    "reason": value.get("reason") or "",
                    "metrics": metrics or (base.get("metrics") if base else {}),
                    "parameters": parameters or (base.get("parameters") if base else {}),
                }
            )
            continue

        if isinstance(value, str):
            base = config_index.get(value)
            if base:
                normalized.append(
                    {
                        "strategy_config_id": value,
                        "strategy_name": base.get("strategy_name") or f"Config {value[:8]}",
                        "reason": "",
                        "metrics": base.get("metrics") or {},
                        "parameters": base.get("parameters") or {},
                    }
                )
            else:
                normalized.append(value)
            continue

        normalized.append(str(value))

    return normalized


def _normalise_report_payload(payload: dict[str, Any], input_summary: dict[str, Any]) -> dict[str, Any]:
    """Apply backward-compatible normalization for AI payload fields."""
    normalized = dict(payload)
    normalized["strongest_configs"] = _normalise_config_items(payload.get("strongest_configs", []), input_summary)
    normalized["weak_configs"] = _normalise_config_items(payload.get("weak_configs", []), input_summary)

    confidence = _normalise_confidence_score(payload.get("confidence_score"))
    if confidence is not None:
        normalized["confidence_score"] = confidence

    return normalized


class AIBacktestReportService:
    """Generate and persist AI-powered research reports for backtest runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def generate_report(
        self,
        backtest_run_id: str,
        request: AIBacktestReportRequest,
    ) -> AIBacktestReportResponse:
        """Generate a new AI report for a backtest run and persist it."""
        run_uuid = uuid.UUID(backtest_run_id)

        run = self._session.get(BacktestRun, run_uuid)
        if run is None:
            raise ValueError(f"BacktestRun {backtest_run_id} not found")

        results = list(
            self._session.execute(
                select(StrategyResult).where(StrategyResult.backtest_run_id == run_uuid)
            ).scalars()
        )

        strategy_config_ids = [r.strategy_config_id for r in results if r.strategy_config_id is not None]
        config_lookup: dict[str, StrategyConfig] = {}
        if strategy_config_ids:
            config_rows = self._session.execute(
                select(StrategyConfig).where(StrategyConfig.id.in_(strategy_config_ids))
            ).scalars()
            config_lookup = {str(cfg.id): cfg for cfg in config_rows}

        input_summary = _build_input_summary(run, results, request.focus, config_lookup=config_lookup)

        settings = get_settings()
        model_name = getattr(settings, "openai_model_name", "gpt-4-turbo")

        report = AIBacktestReport(
            backtest_run_id=run_uuid,
            report_type="comparison_review",
            focus=request.focus,
            status="pending",
            model_name=model_name,
            input_summary=input_summary,
        )
        self._session.add(report)
        self._session.flush()  # get ID before LLM call

        try:
            router = LLMProviderRouter(settings)
            provider = router.get_provider()
            llm_request = LLMRequest(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=_build_user_prompt(input_summary),
                schema=_REPORT_SCHEMA,
                model_name=model_name,
                temperature=0.0,
            )
            response = await provider.generate_structured(llm_request)
            payload = _normalise_report_payload(response.content, input_summary)

            report.status = "completed"
            report.report_json = payload
            report.plain_english_summary = str(payload.get("plain_english_summary", ""))
            report.confidence_score = _normalise_confidence_score(payload.get("confidence_score"))
            report.model_name = getattr(response, "model", model_name) or model_name

        except Exception as exc:
            report.status = "failed"
            report.error_message = str(exc)

        self._session.commit()
        self._session.refresh(report)
        return AIBacktestReportResponse.model_validate(report)

    def list_reports(
        self,
        backtest_run_id: str,
    ) -> AIBacktestReportListResponse:
        """Return all AI reports for a backtest run, newest first."""
        run_uuid = uuid.UUID(backtest_run_id)
        rows = list(
            self._session.execute(
                select(AIBacktestReport)
                .where(AIBacktestReport.backtest_run_id == run_uuid)
                .order_by(AIBacktestReport.created_at.desc())
            ).scalars()
        )
        return AIBacktestReportListResponse(
            total=len(rows),
            items=[AIBacktestReportResponse.model_validate(r) for r in rows],
        )

    def get_report(self, report_id: str) -> AIBacktestReportResponse | None:
        """Return a single report by ID, or None if not found."""
        report = self._session.get(AIBacktestReport, uuid.UUID(report_id))
        if report is None:
            return None
        return AIBacktestReportResponse.model_validate(report)
