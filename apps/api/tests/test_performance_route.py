"""Tests for GET /performance-stats route — QA-224."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.db.session import get_db_session
from app.services.performance_stats_service import (
    DimensionWinRate,
    PerformanceStats,
)


def _mock_session():
    return MagicMock()


def _empty_stats() -> PerformanceStats:
    return PerformanceStats(
        total_trades=0, total_wins=0, overall_win_rate=0.0,
        by_setup=[], by_asset=[], by_catalyst=[], by_regime=[],
    )


def _rich_stats() -> PerformanceStats:
    return PerformanceStats(
        total_trades=50,
        total_wins=28,
        overall_win_rate=0.56,
        by_setup=[DimensionWinRate(key="TREND_PULLBACK", total=30, wins=18, win_rate=0.60)],
        by_asset=[DimensionWinRate(key="asset-uuid", total=15, wins=9, win_rate=0.60)],
        by_catalyst=[DimensionWinRate(key="MACRO", total=20, wins=11, win_rate=0.55)],
        by_regime=[DimensionWinRate(key="TREND", total=35, wins=22, win_rate=0.629)],
    )


# ---------------------------------------------------------------------------
# QA-224 — Performance stats route tests
# ---------------------------------------------------------------------------


def _make_client(stats: PerformanceStats):
    """Build TestClient with mocked PerformanceStatsService."""
    mock_session = _mock_session()
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    with patch(
        "app.api.routes.performance.PerformanceStatsService"
    ) as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.overall_stats.return_value = stats
        mock_svc_cls.return_value = mock_svc

        client = TestClient(app)
        response = client.get("/performance-stats")
        return response


def test_performance_stats_returns_200():
    response = _make_client(_empty_stats())
    assert response.status_code == 200


def test_performance_stats_structure():
    response = _make_client(_rich_stats())
    data = response.json()
    assert "total_trades" in data
    assert "total_wins" in data
    assert "overall_win_rate" in data
    assert "by_setup" in data
    assert "by_asset" in data
    assert "by_catalyst" in data
    assert "by_regime" in data


def test_performance_stats_values():
    response = _make_client(_rich_stats())
    data = response.json()
    assert data["total_trades"] == 50
    assert data["total_wins"] == 28
    assert data["overall_win_rate"] == pytest.approx(0.56, rel=1e-3)


def test_performance_stats_by_setup_correct():
    response = _make_client(_rich_stats())
    data = response.json()
    assert len(data["by_setup"]) == 1
    assert data["by_setup"][0]["key"] == "TREND_PULLBACK"
    assert data["by_setup"][0]["win_rate"] == pytest.approx(0.60, rel=1e-3)
