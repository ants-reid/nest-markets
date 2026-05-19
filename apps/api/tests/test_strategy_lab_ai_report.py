"""Tests for MH-14 AI Backtest Report — service + routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models.ai_backtest_report import AIBacktestReport
from app.db.models.backtest_run import BacktestRun
from app.db.models.strategy_config import StrategyConfig
from app.db.models.strategy_result import StrategyResult
from app.db.session import get_db_session
from app.main import app
from app.schemas.strategy_lab import AIBacktestReportRequest, ResearchWarnings
from app.services.ai_backtest_report_service import (
    AIBacktestReportService,
    _build_input_summary,
    _normalise_confidence_score,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_run(**kwargs) -> MagicMock:
    run_id = uuid.uuid4()
    defaults: dict[str, Any] = dict(
        id=run_id,
        name="Test Backtest",
        status="completed",
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
        requested_assets={"assets": ["AAPL"]},
        requested_timeframes={"timeframes": ["1d"]},
        strategy_config_ids={},
        starting_capital=Decimal("10000"),
        result_summary=None,
        error_message=None,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=BacktestRun)
    for key, value in defaults.items():
        setattr(obj, key, value)
    return obj


def _make_result(backtest_run_id: uuid.UUID, score: float = 50.0, total_trades: int = 20, **kwargs) -> MagicMock:
    defaults: dict[str, Any] = dict(
        id=uuid.uuid4(),
        backtest_run_id=backtest_run_id,
        strategy_config_id=None,
        asset="AAPL",
        timeframe="1d",
        total_trades=total_trades,
        wins=12,
        losses=8,
        breakeven=0,
        win_rate=Decimal("0.6"),
        average_win=Decimal("120.00"),
        average_loss=Decimal("-60.00"),
        profit_factor=Decimal("2.0"),
        expectancy=Decimal("24.0"),
        total_return_pct=Decimal("15.0"),
        max_drawdown_pct=Decimal("-8.0"),
        score=Decimal(str(score)),
        metrics=None,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=StrategyResult)
    for key, value in defaults.items():
        setattr(obj, key, value)
    return obj


def _make_report(
    backtest_run_id: uuid.UUID,
    status: str = "completed",
    **kwargs,
) -> MagicMock:
    now = datetime.now(tz=timezone.utc)
    defaults: dict[str, Any] = dict(
        id=uuid.uuid4(),
        backtest_run_id=backtest_run_id,
        report_type="comparison_review",
        focus="balanced",
        status=status,
        model_name="gpt-4-turbo",
        input_summary={"run_name": "Test Backtest", "config_count": 1},
        report_json={
            "plain_english_summary": "Overall decent performance.",
            "strongest_configs": ["Config A"],
            "weak_configs": [],
            "overfitting_warnings": [],
            "sample_size_warnings": [],
            "risk_notes": [],
            "data_quality_notes": [],
            "recommended_next_tests": ["Test longer time window"],
            "reject_or_continue": "continue_testing",
            "confidence_score": 75.0,
        },
        plain_english_summary="Overall decent performance.",
        confidence_score=Decimal("75.0"),
        error_message=None,
        created_at=now,
        updated_at=now,
        # AIBacktestReportResponse declares research_warnings as a
        # ResearchWarnings model instance with default_factory; if left as
        # MagicMock auto-attr, Pydantic v2 model_validate(from_attributes=True)
        # rejects the non-conforming value.
        research_warnings=ResearchWarnings(),
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=AIBacktestReport)
    for key, value in defaults.items():
        setattr(obj, key, value)
    return obj


# ── Unit: _build_input_summary ─────────────────────────────────────────────


def test_build_input_summary_basic():
    """_build_input_summary produces expected keys."""
    run = _make_run()
    results = [_make_result(run.id, score=70.0), _make_result(run.id, score=30.0)]
    summary = _build_input_summary(run, results, "balanced")

    assert summary["run_name"] == "Test Backtest"
    assert summary["config_count"] == 2
    assert summary["focus"] == "balanced"
    assert "score_distribution" in summary
    assert summary["score_distribution"]["min"] == 30.0
    assert summary["score_distribution"]["max"] == 70.0
    assert len(summary["top_10_configs"]) == 2
    assert summary["bottom_5_configs"] == []  # only populated when > 10 results


def test_build_input_summary_includes_config_parameters_and_metrics():
    """Input summary rows include readable strategy config details and metric bundle."""
    run = _make_run()
    cfg_id = uuid.uuid4()
    result = _make_result(run.id, strategy_config_id=cfg_id, score=77.2, total_trades=122)

    config = MagicMock(spec=StrategyConfig)
    config.id = cfg_id
    config.name = "MA Momentum Fast"
    config.parameters = {
        "fast_window": 3,
        "slow_window": 20,
        "risk_reward": 1.5,
        "hold_bars": 5,
        "risk_per_trade_pct": 0.5,
    }

    summary = _build_input_summary(
        run,
        [result],
        "balanced",
        config_lookup={str(cfg_id): config},
    )

    row = summary["top_10_configs"][0]
    assert row["strategy_config_id"] == str(cfg_id)
    assert row["strategy_name"] == "MA Momentum Fast"
    assert row["parameters"]["fast_window"] == 3
    assert row["metrics"]["total_trades"] == 122
    assert row["metrics"]["score"] == 77.2


def test_build_input_summary_top10_bottom5():
    """Top-10 and bottom-5 are separated when > 10 results."""
    run = _make_run()
    results = [_make_result(run.id, score=float(i * 5)) for i in range(15)]
    summary = _build_input_summary(run, results, "risk")
    assert len(summary["top_10_configs"]) == 10
    assert len(summary["bottom_5_configs"]) == 5


def test_build_input_summary_empty_results():
    """Empty results produce zero-filled stats without crashing."""
    run = _make_run()
    summary = _build_input_summary(run, [], "performance")
    assert summary["config_count"] == 0
    assert summary["score_distribution"] == {}
    assert summary["top_10_configs"] == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0.6, 60.0),
        (60, 60.0),
        (150, 100.0),
    ],
)
def test_confidence_normalization_rules(raw, expected):
    """Confidence is normalized to 0..100 with 0..1 scaled and >100 clamped."""
    assert _normalise_confidence_score(raw) == expected


# ── Unit: AIBacktestReportService ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_report_success():
    """generate_report persists completed report when LLM returns valid data."""
    run_id = uuid.uuid4()
    run = _make_run(id=run_id)
    result = _make_result(run_id)

    session = MagicMock()
    session.get.return_value = run

    scalars_mock = MagicMock()
    scalars_mock.__iter__ = MagicMock(return_value=iter([result]))
    execute_mock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    session.execute.return_value = execute_mock

    session.flush.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None

    mock_response = MagicMock()
    mock_response.content = {
        "plain_english_summary": "Solid performance.",
        "strongest_configs": ["Config A"],
        "weak_configs": [],
        "overfitting_warnings": [],
        "sample_size_warnings": [],
        "risk_notes": [],
        "data_quality_notes": [],
        "recommended_next_tests": [],
        "reject_or_continue": "continue_testing",
        "confidence_score": 80.0,
    }
    mock_response.model = "gpt-4-turbo"

    with patch("app.services.ai_backtest_report_service.AIBacktestReport") as MockReport, \
         patch("app.services.ai_backtest_report_service.LLMProviderRouter") as MockRouter:
        instance = MagicMock()
        instance.backtest_run_id = run_id
        instance.report_type = "comparison_review"
        instance.focus = "balanced"
        instance.status = "completed"
        instance.model_name = "gpt-4-turbo"
        instance.input_summary = {}
        instance.report_json = mock_response.content
        instance.plain_english_summary = "Solid performance."
        instance.confidence_score = Decimal("80.0")
        instance.error_message = None
        instance.id = uuid.uuid4()
        instance.created_at = datetime.now(tz=timezone.utc)
        instance.updated_at = datetime.now(tz=timezone.utc)
        instance.research_warnings = ResearchWarnings()
        MockReport.return_value = instance

        provider = AsyncMock()
        provider.generate_structured = AsyncMock(return_value=mock_response)
        mock_router = MagicMock()
        mock_router.get_provider.return_value = provider
        MockRouter.return_value = mock_router

        svc = AIBacktestReportService(session)
        req = AIBacktestReportRequest(focus="balanced")
        result_response = await svc.generate_report(str(run_id), req)

    assert result_response is not None
    assert instance.status == "completed"
    assert instance.plain_english_summary == "Solid performance."


@pytest.mark.asyncio
async def test_generate_report_backtest_not_found():
    """generate_report raises ValueError when BacktestRun not found."""
    session = MagicMock()
    session.get.return_value = None

    svc = AIBacktestReportService(session)
    req = AIBacktestReportRequest(focus="balanced")

    with pytest.raises(ValueError, match="not found"):
        await svc.generate_report(str(uuid.uuid4()), req)


@pytest.mark.asyncio
async def test_generate_report_llm_failure_persists_failed_status():
    """generate_report marks report as failed when LLM raises an exception."""
    run_id = uuid.uuid4()
    run = _make_run(id=run_id)

    session = MagicMock()
    session.get.return_value = run

    scalars_mock = MagicMock()
    scalars_mock.__iter__ = MagicMock(return_value=iter([]))
    execute_mock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    session.execute.return_value = execute_mock

    with patch("app.services.ai_backtest_report_service.AIBacktestReport") as MockReport, \
         patch("app.services.ai_backtest_report_service.LLMProviderRouter") as MockRouter:
        instance = MagicMock()
        instance.status = "pending"
        instance.id = uuid.uuid4()
        instance.backtest_run_id = run_id
        instance.report_type = "comparison_review"
        instance.focus = "risk"
        instance.model_name = "gpt-4-turbo"
        instance.input_summary = {}
        instance.report_json = None
        instance.plain_english_summary = None
        instance.confidence_score = None
        instance.error_message = None
        instance.created_at = datetime.now(tz=timezone.utc)
        instance.updated_at = datetime.now(tz=timezone.utc)
        instance.research_warnings = ResearchWarnings()
        MockReport.return_value = instance

        MockRouter.side_effect = Exception("API key not configured for OpenAI provider")

        svc = AIBacktestReportService(session)
        req = AIBacktestReportRequest(focus="risk")
        await svc.generate_report(str(run_id), req)

    assert instance.status == "failed"
    assert "API key" in instance.error_message


@pytest.mark.asyncio
async def test_generate_report_normalizes_confidence_to_60_when_raw_point6():
    """LLM confidence in 0..1 range is normalized to percentage scale."""
    run_id = uuid.uuid4()
    run = _make_run(id=run_id)
    result = _make_result(run_id)

    session = MagicMock()
    session.get.return_value = run
    scalars_mock = MagicMock()
    scalars_mock.__iter__ = MagicMock(return_value=iter([result]))
    execute_mock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    session.execute.return_value = execute_mock
    session.flush.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None

    mock_response = MagicMock()
    mock_response.model = "gpt-4-turbo"
    mock_response.content = {
        "plain_english_summary": "Summary",
        "strongest_configs": [str(result.strategy_config_id)],
        "weak_configs": [],
        "overfitting_warnings": [],
        "sample_size_warnings": [],
        "risk_notes": [],
        "data_quality_notes": [],
        "recommended_next_tests": [],
        "reject_or_continue": "continue_testing",
        "confidence_score": 0.6,
    }

    with patch("app.services.ai_backtest_report_service.AIBacktestReport") as MockReport, \
         patch("app.services.ai_backtest_report_service.LLMProviderRouter") as MockRouter:
        instance = MagicMock()
        instance.id = uuid.uuid4()
        instance.backtest_run_id = run_id
        instance.report_type = "comparison_review"
        instance.focus = "balanced"
        instance.status = "completed"
        instance.model_name = "gpt-4-turbo"
        instance.input_summary = {}
        instance.report_json = {}
        instance.plain_english_summary = "Summary"
        instance.confidence_score = None
        instance.error_message = None
        instance.created_at = datetime.now(tz=timezone.utc)
        instance.updated_at = datetime.now(tz=timezone.utc)
        instance.research_warnings = ResearchWarnings()
        MockReport.return_value = instance

        provider = AsyncMock()
        provider.generate_structured = AsyncMock(return_value=mock_response)
        router = MagicMock()
        router.get_provider.return_value = provider
        MockRouter.return_value = router

        svc = AIBacktestReportService(session)
        resp = await svc.generate_report(str(run_id), AIBacktestReportRequest(focus="balanced"))

    assert instance.confidence_score == 60.0
    assert resp.confidence_score == 60.0


@pytest.mark.asyncio
async def test_generate_report_keeps_string_config_outputs_backward_compatible():
    """Legacy strongest/weak string outputs remain valid after normalization."""
    run_id = uuid.uuid4()
    run = _make_run(id=run_id)
    result = _make_result(run_id)

    session = MagicMock()
    session.get.return_value = run
    scalars_mock = MagicMock()
    scalars_mock.__iter__ = MagicMock(return_value=iter([result]))
    execute_mock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    session.execute.return_value = execute_mock
    session.flush.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None

    mock_response = MagicMock()
    mock_response.model = "gpt-4-turbo"
    mock_response.content = {
        "plain_english_summary": "Summary",
        "strongest_configs": ["legacy-config-id"],
        "weak_configs": ["legacy-config-id-2"],
        "overfitting_warnings": [],
        "sample_size_warnings": [],
        "risk_notes": [],
        "data_quality_notes": [],
        "recommended_next_tests": [],
        "reject_or_continue": "continue_testing",
        "confidence_score": 60,
    }

    with patch("app.services.ai_backtest_report_service.AIBacktestReport") as MockReport, \
         patch("app.services.ai_backtest_report_service.LLMProviderRouter") as MockRouter:
        instance = MagicMock()
        instance.id = uuid.uuid4()
        instance.backtest_run_id = run_id
        instance.report_type = "comparison_review"
        instance.focus = "balanced"
        instance.status = "completed"
        instance.model_name = "gpt-4-turbo"
        instance.input_summary = {}
        instance.report_json = {}
        instance.plain_english_summary = "Summary"
        instance.confidence_score = None
        instance.error_message = None
        instance.created_at = datetime.now(tz=timezone.utc)
        instance.updated_at = datetime.now(tz=timezone.utc)
        instance.research_warnings = ResearchWarnings()
        MockReport.return_value = instance

        provider = AsyncMock()
        provider.generate_structured = AsyncMock(return_value=mock_response)
        router = MagicMock()
        router.get_provider.return_value = provider
        MockRouter.return_value = router

        svc = AIBacktestReportService(session)
        await svc.generate_report(str(run_id), AIBacktestReportRequest(focus="balanced"))

    assert isinstance(instance.report_json["strongest_configs"][0], str)
    assert isinstance(instance.report_json["weak_configs"][0], str)


def test_list_reports_returns_all_for_run():
    """list_reports returns all reports for a run, newest first."""
    run_id = uuid.uuid4()
    report1 = _make_report(run_id)
    report2 = _make_report(run_id)

    session = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.__iter__ = MagicMock(return_value=iter([report1, report2]))
    execute_mock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    session.execute.return_value = execute_mock

    svc = AIBacktestReportService(session)
    result = svc.list_reports(str(run_id))

    assert result.total == 2
    assert len(result.items) == 2


def test_get_report_not_found_returns_none():
    """get_report returns None for a missing report ID."""
    session = MagicMock()
    session.get.return_value = None

    svc = AIBacktestReportService(session)
    assert svc.get_report(str(uuid.uuid4())) is None


def test_get_report_returns_response():
    """get_report returns a validated response for an existing report."""
    run_id = uuid.uuid4()
    report = _make_report(run_id)

    session = MagicMock()
    session.get.return_value = report

    svc = AIBacktestReportService(session)
    result = svc.get_report(str(report.id))

    assert result is not None
    assert result.status == "completed"


# ── Route integration tests ────────────────────────────────────────────────


@pytest.fixture()
def http_client():
    """HTTP test client with mock DB session injected."""
    mock_session = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: (yield mock_session)
    try:
        with TestClient(app) as c:
            yield c, mock_session
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_generate_ai_report_route_not_found(http_client):
    """POST /strategy-lab/backtests/{id}/ai-report returns 404 for unknown run."""
    c, session = http_client
    session.get.return_value = None

    resp = c.post(
        f"/strategy-lab/backtests/{uuid.uuid4()}/ai-report",
        json={"focus": "balanced"},
    )
    assert resp.status_code == 404


def test_list_ai_reports_route(http_client):
    """GET /strategy-lab/backtests/{id}/ai-reports returns a list response."""
    c, session = http_client
    run_id = uuid.uuid4()

    scalars_mock = MagicMock()
    scalars_mock.__iter__ = MagicMock(return_value=iter([]))
    execute_mock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    session.execute.return_value = execute_mock

    resp = c.get(f"/strategy-lab/backtests/{run_id}/ai-reports")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_get_ai_report_route_not_found(http_client):
    """GET /strategy-lab/ai-reports/{id} returns 404 for unknown report."""
    c, session = http_client
    session.get.return_value = None

    resp = c.get(f"/strategy-lab/ai-reports/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_ai_report_route_returns_report(http_client):
    """GET /strategy-lab/ai-reports/{id} returns report data."""
    c, session = http_client
    run_id = uuid.uuid4()
    report = _make_report(run_id)
    session.get.return_value = report

    resp = c.get(f"/strategy-lab/ai-reports/{report.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "confidence_score" in data
