"""Phase 8 — Scoring Engine V2 tests."""

from __future__ import annotations

import pytest

from app.services.runtime.scoring.score_resolver import ScoreResolver, ScoringConfig
from app.services.runtime.scoring.score_explainer import ScoreExplainer
from app.services.runtime.scoring.score_bucket_service import ScoreBucketService
from app.services.runtime.scoring.score_calibration_service import ScoreCalibrationService
from app.services.runtime.scoring.score_threshold_service import ScoreThresholdService, ThresholdConfig
from app.services.runtime.scoring.dnt_probability_service import DNTProbabilityService, DNTInput


# ---------------------------------------------------------------------------
# ScoreResolver
# ---------------------------------------------------------------------------

class TestScoreResolver:
    def test_returns_scoring_config(self):
        resolver = ScoreResolver()
        config = resolver.resolve("equity/momentum/1D")
        assert isinstance(config, ScoringConfig)
        assert config.bucket == "equity/momentum/1D"

    def test_weights_sum_to_one(self):
        config = ScoreResolver().resolve("equity/momentum/1D")
        assert sum(config.weights.values()) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# ScoreExplainer
# ---------------------------------------------------------------------------

class TestScoreExplainer:
    _WEIGHTS = {"momentum": 0.40, "risk": 0.30, "news": 0.10, "execution": 0.20}

    def test_final_score_weighted_sum(self):
        scores = {"momentum": 1.0, "risk": 0.0, "news": 0.5, "execution": 0.5}
        expl = ScoreExplainer().explain(scores, self._WEIGHTS)
        expected = 1.0 * 0.40 + 0.0 * 0.30 + 0.5 * 0.10 + 0.5 * 0.20
        assert expl.final_score == pytest.approx(expected)

    def test_dominant_factor_highest_contribution(self):
        scores = {"momentum": 1.0, "risk": 0.1, "news": 0.1, "execution": 0.1}
        expl = ScoreExplainer().explain(scores, self._WEIGHTS)
        assert expl.dominant_factor == "momentum"

    def test_narrative_is_string(self):
        scores = {"momentum": 0.7, "risk": 0.5, "news": 0.4, "execution": 0.6}
        expl = ScoreExplainer().explain(scores, self._WEIGHTS)
        assert isinstance(expl.narrative, str)


# ---------------------------------------------------------------------------
# ScoreBucketService
# ---------------------------------------------------------------------------

class TestScoreBucketService:
    def test_assign_normalises_case(self):
        svc = ScoreBucketService()
        assert svc.assign("EQUITY", "MOMENTUM", "1d") == "equity/momentum/1D"

    def test_parse_valid_bucket(self):
        svc = ScoreBucketService()
        assert svc.parse("equity/momentum/1D") == ("equity", "momentum", "1D")

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            ScoreBucketService().parse("equity/momentum")


# ---------------------------------------------------------------------------
# ScoreCalibrationService
# ---------------------------------------------------------------------------

class TestScoreCalibrationService:
    def test_perfect_brier_score(self):
        svc = ScoreCalibrationService()
        result = svc.brier_score([1.0, 0.0], [1.0, 0.0])
        assert result == pytest.approx(0.0)

    def test_worst_brier_score(self):
        svc = ScoreCalibrationService()
        result = svc.brier_score([1.0, 0.0], [0.0, 1.0])
        assert result == pytest.approx(1.0)

    def test_calibration_summary_keys(self):
        svc = ScoreCalibrationService()
        summary = svc.calibration_summary([0.6, 0.4, 0.7], [1.0, 0.0, 1.0])
        assert {"brier_score", "log_loss", "mean_predicted", "mean_actual", "n"} <= summary.keys()


# ---------------------------------------------------------------------------
# ScoreThresholdService
# ---------------------------------------------------------------------------

class TestScoreThresholdService:
    def test_passes_above_threshold(self):
        svc = ScoreThresholdService()
        assert svc.passes("equity/momentum/1D", score=0.75) is True

    def test_fails_below_threshold(self):
        svc = ScoreThresholdService()
        assert svc.passes("equity/momentum/1D", score=0.45) is False

    def test_custom_bucket_threshold(self):
        svc = ScoreThresholdService()
        svc.register("equity/breakout/1D", ThresholdConfig(min_score=0.80))
        assert svc.passes("equity/breakout/1D", score=0.75) is False
        assert svc.passes("equity/breakout/1D", score=0.85) is True


# ---------------------------------------------------------------------------
# DNTProbabilityService
# ---------------------------------------------------------------------------

class TestDNTProbabilityService:
    def test_high_score_low_vix_low_dnt(self):
        svc = DNTProbabilityService()
        dnt = svc.estimate(DNTInput(score=0.9, vix=12, regime="risk_on"))
        assert dnt < 0.20

    def test_low_score_high_vix_high_dnt(self):
        svc = DNTProbabilityService()
        dnt = svc.estimate(DNTInput(score=0.3, vix=35, regime="high_vol"))
        assert dnt > 0.80

    def test_event_imminent_increases_dnt(self):
        svc = DNTProbabilityService()
        dnt_no_event = svc.estimate(DNTInput(score=0.7, vix=18, regime="chop"))
        dnt_event = svc.estimate(DNTInput(score=0.7, vix=18, regime="chop", days_to_event=0))
        assert dnt_event > dnt_no_event

    def test_dnt_in_range(self):
        svc = DNTProbabilityService()
        for score in [0.0, 0.5, 1.0]:
            for vix in [10, 20, 35]:
                dnt = svc.estimate(DNTInput(score=score, vix=vix, regime="chop"))
                assert 0.0 <= dnt <= 1.0
