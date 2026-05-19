"""Tests for PerformanceStatsService — QA-219.

Tests use a mock SQLAlchemy session. Fixture outcomes feed the aggregate
queries via MagicMock side_effect chaining.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.performance_stats_service import (
    PerformanceStatsService,
    _win_rate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(key, total: int, wins: int):
    """Produce a mock row mimicking SQLAlchemy Row with positional + attribute access."""
    r = MagicMock()
    r.__getitem__ = lambda self, idx: key
    r.total = total
    r.wins = wins
    return r


def _mock_execute(total: int, wins: int, dimension_rows=None):
    """Return a mock session whose execute().all() returns the given rows."""
    mock_session = MagicMock()

    if dimension_rows is None:
        dimension_rows = []

    overall_row = MagicMock()
    overall_row.total = total
    overall_row.wins = wins

    execute_result_overall = MagicMock()
    execute_result_overall.one.return_value = overall_row

    execute_result_dim = MagicMock()
    execute_result_dim.all.return_value = dimension_rows

    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        # First call used by _overall_count (uses .one()), subsequent by dimension queries
        if call_count[0] == 1:
            return execute_result_overall
        return execute_result_dim

    mock_session.execute.side_effect = execute_side_effect
    return mock_session


# ---------------------------------------------------------------------------
# QA-219 — PerformanceStatsService unit tests
# ---------------------------------------------------------------------------


def test_win_rate_helper_basic():
    assert _win_rate(5, 10) == 0.5
    assert _win_rate(0, 0) == 0.0
    assert _win_rate(10, 10) == 1.0


def test_overall_stats_empty_database():
    mock_session = _mock_execute(total=0, wins=0)
    service = PerformanceStatsService(mock_session)
    stats = service.overall_stats(min_samples=1)
    assert stats.total_trades == 0
    assert stats.total_wins == 0
    assert stats.overall_win_rate == 0.0


def test_overall_stats_correct_win_rate():
    mock_session = _mock_execute(total=20, wins=12)
    service = PerformanceStatsService(mock_session)
    stats = service.overall_stats(min_samples=0)
    assert stats.overall_win_rate == pytest.approx(0.6, rel=1e-4)


def test_dimension_excluded_below_min_samples():
    """Dimensions with < min_samples outcomes must be excluded."""
    dim_row = _row("TREND_PULLBACK", total=5, wins=3)
    mock_session = _mock_execute(total=5, wins=3, dimension_rows=[dim_row])
    PerformanceStatsService(mock_session)
    # Directly test the dimension builder
    results = PerformanceStatsService._to_dimension([dim_row], min_samples=10)
    assert results == []


def test_dimension_included_at_min_samples():
    """Dimension exactly at min_samples boundary must be included."""
    dim_row = _row("TREND_PULLBACK", total=10, wins=6)
    results = PerformanceStatsService._to_dimension([dim_row], min_samples=10)
    assert len(results) == 1
    assert results[0].key == "TREND_PULLBACK"
    assert results[0].win_rate == pytest.approx(0.6, rel=1e-4)
