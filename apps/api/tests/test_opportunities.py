"""Tests for OpportunityRankerService and GET /opportunities — QA-207/208."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.enums import AssetClass, HorizonLabel, RegimeType, SetupType, SignalStatus, TradeDirection
from app.db.models.asset import Asset
from app.db.models.signal import Signal
from app.db.session import get_db_session
from app.main import app
from app.services.opportunity_ranker_service import OpportunityRankerService
from app.services.runtime.scoring_service import ScoringService

_scoring_svc = ScoringService()


def _composite_score(signal, *, historical_win_rate: float = 0.50) -> float:
    """Adapter shim so existing tests continue working after _composite_score was extracted."""
    return _scoring_svc.composite_score(
        signal_score=float(signal.signal_score),
        confidence=float(signal.confidence),
        catalyst_score=float(signal.catalyst_score),
        historical_win_rate=historical_win_rate,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    *,
    signal_score: float = 75.0,
    confidence: float = 0.80,
    catalyst_score: float = 0.70,
    status: SignalStatus = SignalStatus.CANDIDATE,
) -> MagicMock:
    s = MagicMock(spec=Signal)
    s.id = uuid.uuid4()
    s.signal_score = Decimal(str(signal_score))
    s.confidence = Decimal(str(confidence))
    s.catalyst_score = Decimal(str(catalyst_score))
    s.signal_status = status
    s.direction = TradeDirection.LONG
    s.setup_type = SetupType.TREND_PULLBACK
    s.regime = RegimeType.TREND
    s.horizon_label = HorizonLabel.INTRADAY
    s.entry_min = Decimal("1.0810")
    s.entry_max = Decimal("1.0820")
    s.stop_price = Decimal("1.0790")
    s.target_price = Decimal("1.0850")
    s.scan_ts = datetime.now(UTC)
    return s


def _make_asset(symbol: str = "EURUSD") -> MagicMock:
    a = MagicMock(spec=Asset)
    a.id = uuid.uuid4()
    a.symbol = symbol
    a.asset_class = AssetClass.FX
    return a


# ---------------------------------------------------------------------------
# QA-207 — OpportunityRankerService unit tests
# ---------------------------------------------------------------------------


def test_composite_score_calculation():
    """Composite score: 40% signal_score + 30% confidence + 10% catalyst + 20% hist_win_rate."""
    signal = _make_signal(signal_score=100.0, confidence=1.0, catalyst_score=1.0)
    # With neutral win rate (0.50): 0.40 + 0.30 + 0.10 + 0.20*0.50 = 0.90 → 90.0
    score = _composite_score(signal, historical_win_rate=0.50)
    assert abs(score - 90.0) < 0.01
    # With perfect win rate (1.0) all factors at max → 100.0
    score_perfect = _composite_score(signal, historical_win_rate=1.0)
    assert abs(score_perfect - 100.0) < 0.01


def test_composite_score_zero_inputs():
    """All-zero LLM factors with no history produce 10.0 (neutral 0.50 win-rate contribution)."""
    signal = _make_signal(signal_score=0.0, confidence=0.0, catalyst_score=0.0)
    # 0.20 * 0.50 * 100 = 10.0
    assert _composite_score(signal) == pytest.approx(10.0, abs=0.01)
    # With a known win rate of 0.0 the score collapses to 0
    assert _composite_score(signal, historical_win_rate=0.0) == 0.0


def test_rank_returns_sorted_by_score():
    """rank() must return items sorted by composite score descending."""
    mock_session = MagicMock()

    high_signal = _make_signal(signal_score=90.0, confidence=0.90, catalyst_score=0.80)
    low_signal = _make_signal(signal_score=55.0, confidence=0.55, catalyst_score=0.50)
    asset = _make_asset()

    mock_session.execute.return_value.all.return_value = [
        (low_signal, asset),
        (high_signal, asset),
    ]

    service = OpportunityRankerService(mock_session)
    results = service.rank(limit=10)

    assert len(results) == 2
    assert results[0].score > results[1].score


def test_rank_respects_limit():
    """rank() must return at most limit items."""
    mock_session = MagicMock()
    asset = _make_asset()
    rows = [((_make_signal(signal_score=70.0 + i), asset)) for i in range(10)]
    mock_session.execute.return_value.all.return_value = rows

    service = OpportunityRankerService(mock_session)
    results = service.rank(limit=3)
    assert len(results) <= 3


def test_rank_empty_returns_empty_list():
    """rank() returns [] when no candidates exist."""
    mock_session = MagicMock()
    mock_session.execute.return_value.all.return_value = []

    service = OpportunityRankerService(mock_session)
    assert service.rank() == []


# ---------------------------------------------------------------------------
# QA-208 — GET /opportunities route
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    mock_session = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: (yield mock_session)
    try:
        with TestClient(app) as c:
            yield c, mock_session
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_get_opportunities_returns_200(client):
    c, session = client
    session.execute.return_value.all.return_value = []

    resp = c.get("/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_get_opportunities_returns_ranked_items(client):
    c, session = client

    signal = _make_signal(signal_score=80.0)
    asset = _make_asset("EURUSD")
    session.execute.return_value.all.return_value = [(signal, asset)]

    resp = c.get("/opportunities?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["asset"] == "EURUSD"
    assert item["direction"] == "long"
    assert item["score"] > 0


def test_get_opportunities_limit_validation(client):
    c, _ = client
    resp = c.get("/opportunities?limit=0")
    assert resp.status_code == 422


def test_get_opportunities_limit_max_validation(client):
    c, _ = client
    resp = c.get("/opportunities?limit=999")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# P1 fix: historical win rate factor
# ---------------------------------------------------------------------------


def test_rank_uses_historical_win_rate_when_injected():
    """Higher historical win rate should boost composite score."""
    from unittest.mock import MagicMock as MM
    from app.services.performance_stats_service import DimensionWinRate, PerformanceStatsService
    from app.db.enums import SetupType

    mock_session = MM()
    signal = _make_signal(signal_score=70.0, confidence=0.70, catalyst_score=0.60)
    signal.setup_type = SetupType.TREND_PULLBACK
    asset = _make_asset()
    mock_session.execute.return_value.all.return_value = [(signal, asset)]

    # No stats injected — neutral prior
    svc_no_stats = OpportunityRankerService(mock_session)
    results_no_stats = svc_no_stats.rank(limit=1)

    # High historical win rate (80%) injected
    mock_perf = MM(spec=PerformanceStatsService)
    mock_perf.win_rate_by_setup.return_value = [
        DimensionWinRate(key=SetupType.TREND_PULLBACK.value, total=20, wins=16, win_rate=0.80)
    ]
    svc_with_stats = OpportunityRankerService(mock_session, performance_stats=mock_perf)
    results_with_stats = svc_with_stats.rank(limit=1)

    assert results_with_stats[0].score > results_no_stats[0].score


def test_rank_uses_neutral_prior_with_no_stats_service():
    """rank() applies neutral 0.50 win rate when no PerformanceStatsService is injected."""
    mock_session = MagicMock()
    signal = _make_signal(signal_score=100.0, confidence=1.0, catalyst_score=1.0)
    asset = _make_asset()
    mock_session.execute.return_value.all.return_value = [(signal, asset)]

    svc = OpportunityRankerService(mock_session, performance_stats=None)
    results = svc.rank(limit=1)

    # Max LLM factors + neutral 0.50 win rate = 0.40 + 0.30 + 0.10 + 0.10 = 0.90 → 90.0
    assert results[0].score == pytest.approx(90.0, abs=0.1)


def test_rank_low_win_rate_setup_ranked_below_high_win_rate():
    """A setup with poor history should rank below an equivalent one with good history."""
    from app.services.performance_stats_service import DimensionWinRate, PerformanceStatsService
    from app.db.enums import SetupType

    mock_session = MagicMock()
    asset = _make_asset()

    # Both signals have identical LLM scores
    sig_a = _make_signal(signal_score=75.0, confidence=0.75, catalyst_score=0.60)
    sig_a.setup_type = SetupType.TREND_PULLBACK

    sig_b = _make_signal(signal_score=75.0, confidence=0.75, catalyst_score=0.60)
    sig_b.setup_type = SetupType.BREAKOUT_CONFIRMATION

    mock_session.execute.return_value.all.return_value = [(sig_a, asset), (sig_b, asset)]

    mock_perf = MagicMock(spec=PerformanceStatsService)
    mock_perf.win_rate_by_setup.return_value = [
        DimensionWinRate(key=SetupType.TREND_PULLBACK.value, total=30, wins=25, win_rate=0.83),
        DimensionWinRate(key=SetupType.BREAKOUT_CONFIRMATION.value, total=25, wins=8, win_rate=0.32),
    ]

    svc = OpportunityRankerService(mock_session, performance_stats=mock_perf)
    results = svc.rank(limit=2)

    assert results[0].setup_type == SetupType.TREND_PULLBACK.value
    assert results[1].setup_type == SetupType.BREAKOUT_CONFIRMATION.value
