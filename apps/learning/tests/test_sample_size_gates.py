"""Tests for sample size policy gate (Phase 10)."""
import pytest

from apps.learning.services.validation.sample_size_policy_service import (
    SampleSizePolicy,
    SampleSizePolicyService,
)


class TestSampleSizePolicyService:
    def setup_method(self):
        self.svc = SampleSizePolicyService(SampleSizePolicy(
            regime_model=100,
            scoring_model=200,
            execution_model=100,
            walk_forward_per_fold=50,
        ))

    def test_passes_when_sufficient(self):
        result = self.svc.check("scoring_model", 300)
        assert result.passed is True
        assert result.required == 200

    def test_fails_when_insufficient(self):
        result = self.svc.check("scoring_model", 50)
        assert result.passed is False
        assert "50" in result.reason

    def test_exact_threshold_passes(self):
        result = self.svc.check("regime_model", 100)
        assert result.passed is True

    def test_one_below_threshold_fails(self):
        result = self.svc.check("regime_model", 99)
        assert result.passed is False

    def test_invalid_model_type_raises(self):
        with pytest.raises(ValueError, match="Unknown model_type"):
            self.svc.check("unknown_model", 500)

    def test_check_all_returns_list(self):
        results = self.svc.check_all({
            "regime_model": 150,
            "scoring_model": 100,
        })
        assert len(results) == 2
        passed = {r.model_type: r.passed for r in results}
        assert passed["regime_model"] is True
        assert passed["scoring_model"] is False
