"""Tests for ModelPolicyService promotion gates (Phase 11)."""
import pytest

from app.services.governance.model_policy_service import (
    ModelPolicyService,
    PromotionPolicy,
)


class TestModelPolicyService:
    def setup_method(self):
        policy = PromotionPolicy(
            min_primary_metric={"regime": 0.65, "scoring": 0.62, "execution": 0.65},
            max_brier_score={"regime": 0.22, "scoring": 0.22, "execution": 0.25},
            min_walk_forward_folds=3,
            require_shadow_comparison=True,
            min_shadow_improvement_pct=0.0,
        )
        self.svc = ModelPolicyService(policy=policy)

    def _passing_metrics(self) -> dict:
        return {"primary_metric": 0.70, "brier_score": 0.18}

    def test_all_gates_pass(self):
        result = self.svc.evaluate(
            "scoring",
            metrics=self._passing_metrics(),
            n_walk_forward_folds=5,
            shadow_improvement_pct=0.02,
        )
        assert result.overall_passed is True
        assert "passed" in result.summary.lower()

    def test_primary_metric_gate_fails(self):
        result = self.svc.evaluate(
            "scoring",
            metrics={"primary_metric": 0.50},
            n_walk_forward_folds=5,
            shadow_improvement_pct=0.02,
        )
        assert result.overall_passed is False
        failed = {c.rule for c in result.checks if not c.passed}
        assert "min_primary_metric" in failed

    def test_brier_score_gate_fails(self):
        result = self.svc.evaluate(
            "scoring",
            metrics={"primary_metric": 0.70, "brier_score": 0.30},
            n_walk_forward_folds=5,
            shadow_improvement_pct=0.02,
        )
        assert result.overall_passed is False
        failed = {c.rule for c in result.checks if not c.passed}
        assert "max_brier_score" in failed

    def test_walk_forward_gate_fails(self):
        result = self.svc.evaluate(
            "regime",
            metrics=self._passing_metrics(),
            n_walk_forward_folds=1,
            shadow_improvement_pct=0.01,
        )
        assert result.overall_passed is False
        failed = {c.rule for c in result.checks if not c.passed}
        assert "min_walk_forward_folds" in failed

    def test_shadow_missing_fails(self):
        result = self.svc.evaluate(
            "regime",
            metrics=self._passing_metrics(),
            n_walk_forward_folds=5,
            shadow_improvement_pct=None,
        )
        assert result.overall_passed is False
        failed = {c.rule for c in result.checks if not c.passed}
        assert "shadow_comparison" in failed

    def test_invalid_model_type_raises(self):
        with pytest.raises(ValueError, match="Invalid model_type"):
            self.svc.evaluate("unknown", {})

    def test_brier_score_not_required_when_absent(self):
        """No brier_score in metrics → brier gate not applied."""
        result = self.svc.evaluate(
            "scoring",
            metrics={"primary_metric": 0.70},
            n_walk_forward_folds=5,
            shadow_improvement_pct=0.01,
        )
        rules = {c.rule for c in result.checks}
        assert "max_brier_score" not in rules
        assert result.overall_passed is True

    def test_all_checks_have_rule_and_reason(self):
        result = self.svc.evaluate(
            "execution",
            metrics=self._passing_metrics(),
            n_walk_forward_folds=5,
            shadow_improvement_pct=0.05,
        )
        for check in result.checks:
            assert check.rule
            assert check.reason
