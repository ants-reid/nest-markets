"""Tests for walk-forward validation pipeline (Phase 10)."""
import pytest

from apps.learning.pipelines.validate_walk_forward import (
    WalkForwardConfig,
    WalkForwardValidator,
)
from apps.learning.services.validation.walk_forward_validator import (
    WalkForwardValidatorService,
)


def _make_rows(n: int) -> list[dict]:
    return [{"date": f"2023-{i % 12 + 1:02d}-01", "feature": float(i)} for i in range(n)]


class TestWalkForwardValidator:
    def test_basic_validation_passes(self):
        validator = WalkForwardValidator(WalkForwardConfig(n_folds=3, min_train_samples=50))
        rows = _make_rows(300)
        result = validator.validate(rows, pass_threshold=0.50)
        assert result.n_folds >= 1
        assert result.mean_metric > 0
        assert result.passed is True

    def test_raises_on_insufficient_data(self):
        validator = WalkForwardValidator(WalkForwardConfig(min_train_samples=500))
        rows = _make_rows(10)
        with pytest.raises(ValueError, match="Not enough rows"):
            validator.validate(rows)

    def test_fold_results_populated(self):
        validator = WalkForwardValidator(WalkForwardConfig(n_folds=2, min_train_samples=30))
        result = validator.validate(_make_rows(200))
        assert len(result.fold_results) >= 1
        for fold in result.fold_results:
            assert fold.metric > 0
            assert fold.n_train > 0

    def test_mean_metric_between_min_and_max(self):
        validator = WalkForwardValidator(WalkForwardConfig(n_folds=3, min_train_samples=20))
        result = validator.validate(_make_rows(150))
        assert result.min_metric <= result.mean_metric <= result.max_metric

    def test_fails_when_threshold_too_high(self):
        validator = WalkForwardValidator(WalkForwardConfig(n_folds=2, min_train_samples=20))
        result = validator.validate(_make_rows(100), pass_threshold=0.99)
        assert result.passed is False


class TestWalkForwardValidatorService:
    def test_service_wraps_validator(self):
        svc = WalkForwardValidatorService(WalkForwardConfig(n_folds=2, min_train_samples=20))
        report = svc.run(_make_rows(100))
        assert report.gate_passed is True
        assert "auc" in report.gate_reason.lower() or "threshold" in report.gate_reason.lower()

    def test_service_fails_with_high_threshold(self):
        svc = WalkForwardValidatorService(WalkForwardConfig(n_folds=2, min_train_samples=20))
        report = svc.run(_make_rows(100), pass_threshold=0.99)
        assert report.gate_passed is False
