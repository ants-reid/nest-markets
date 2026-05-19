"""Tests for ScoringService and ScoringConfigService — QA-300 through QA-304."""

from __future__ import annotations

import pytest

from app.services.runtime.scoring_config_service import (
    DEFAULT_WEIGHTS,
    ScoringConfigService,
    ScoringWeights,
)
from app.services.runtime.scoring_service import ScoringService, MIN_SIGNAL_SCORE


# ---------------------------------------------------------------------------
# ScoringWeights validation
# ---------------------------------------------------------------------------


def test_default_weights_sum_to_one() -> None:
    w = DEFAULT_WEIGHTS
    assert abs((w.signal_score + w.confidence + w.catalyst_score + w.historical_win_rate) - 1.0) < 1e-6


def test_scoring_weights_validate_passes_on_valid() -> None:
    w = ScoringWeights(signal_score=0.25, confidence=0.25, catalyst_score=0.25, historical_win_rate=0.25)
    w.validate()  # should not raise


def test_scoring_weights_validate_raises_on_bad_sum() -> None:
    w = ScoringWeights(signal_score=0.5, confidence=0.5, catalyst_score=0.1, historical_win_rate=0.1)
    with pytest.raises(ValueError, match="must sum to 1.0"):
        w.validate()


# ---------------------------------------------------------------------------
# ScoringConfigService
# ---------------------------------------------------------------------------


def test_config_service_returns_default_weights() -> None:
    svc = ScoringConfigService()
    w = svc.get_active_weights()
    assert w.signal_score == 0.40
    assert w.confidence == 0.30
    assert w.catalyst_score == 0.10
    assert w.historical_win_rate == 0.20


def test_config_service_build_weights_valid() -> None:
    svc = ScoringConfigService()
    w = svc.build_weights(
        signal_score=0.50, confidence=0.25, catalyst_score=0.15, historical_win_rate=0.10
    )
    assert abs(w.signal_score - 0.50) < 1e-9


def test_config_service_build_weights_invalid_raises() -> None:
    svc = ScoringConfigService()
    with pytest.raises(ValueError):
        svc.build_weights(signal_score=0.9, confidence=0.9, catalyst_score=0.1, historical_win_rate=0.1)


# ---------------------------------------------------------------------------
# ScoringService.composite_score
# ---------------------------------------------------------------------------


def test_composite_score_with_default_weights() -> None:
    svc = ScoringService()
    # signal_score=80, conf=0.8, catalyst=0.7, hist_wr=0.6
    score = svc.composite_score(
        signal_score=80.0,
        confidence=0.8,
        catalyst_score=0.7,
        historical_win_rate=0.6,
    )
    # Expected: 0.40*(80/100) + 0.30*0.8 + 0.10*0.7 + 0.20*0.6 = 0.32+0.24+0.07+0.12 = 0.75 → 75.0
    assert abs(score - 75.0) < 0.01


def test_composite_score_clamps_to_100() -> None:
    svc = ScoringService()
    score = svc.composite_score(
        signal_score=100.0, confidence=1.0, catalyst_score=1.0, historical_win_rate=1.0
    )
    assert score == 100.0


def test_composite_score_clamps_to_0() -> None:
    svc = ScoringService()
    score = svc.composite_score(
        signal_score=0.0, confidence=0.0, catalyst_score=0.0, historical_win_rate=0.0
    )
    assert score == 0.0


def test_composite_score_uses_neutral_prior_by_default() -> None:
    svc = ScoringService()
    # historical_win_rate defaults to 0.5 (neutral prior)
    score_default = svc.composite_score(
        signal_score=50.0, confidence=0.5, catalyst_score=0.5
    )
    score_explicit = svc.composite_score(
        signal_score=50.0, confidence=0.5, catalyst_score=0.5, historical_win_rate=0.5
    )
    assert abs(score_default - score_explicit) < 1e-6


def test_composite_score_custom_weights() -> None:
    svc = ScoringService()
    custom = ScoringWeights(signal_score=1.0, confidence=0.0, catalyst_score=0.0, historical_win_rate=0.0)
    score = svc.composite_score(
        signal_score=60.0, confidence=0.9, catalyst_score=0.9, historical_win_rate=0.9,
        weights=custom,
    )
    # Only signal_score contributes: 60 → 60.0
    assert abs(score - 60.0) < 0.01


# ---------------------------------------------------------------------------
# ScoringService.is_tradeable
# ---------------------------------------------------------------------------


def test_is_tradeable_above_threshold() -> None:
    svc = ScoringService()
    assert svc.is_tradeable(MIN_SIGNAL_SCORE) is True
    assert svc.is_tradeable(MIN_SIGNAL_SCORE + 1) is True


def test_is_tradeable_below_threshold() -> None:
    svc = ScoringService()
    assert svc.is_tradeable(MIN_SIGNAL_SCORE - 1) is False
    assert svc.is_tradeable(0.0) is False


# ---------------------------------------------------------------------------
# ScoringService.explain
# ---------------------------------------------------------------------------


def test_explain_returns_correct_structure() -> None:
    svc = ScoringService()
    result = svc.explain(
        signal_score=80.0, confidence=0.8, catalyst_score=0.7, historical_win_rate=0.6
    )
    assert "composite_score" in result
    assert "contributions" in result
    assert "weights" in result
    assert "inputs" in result
    # Verify contributions sum approximately to composite_score
    contribs = result["contributions"]
    total_contrib = sum(contribs.values())
    assert abs(total_contrib - result["composite_score"]) < 0.01


def test_explain_inputs_match_provided_values() -> None:
    svc = ScoringService()
    result = svc.explain(signal_score=75.0, confidence=0.65, catalyst_score=0.55)
    assert result["inputs"]["signal_score"] == 75.0
    assert result["inputs"]["confidence"] == 0.65
    assert result["inputs"]["catalyst_score"] == 0.55
