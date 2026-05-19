"""Tests for data leakage detection in training pipelines (Phase 10)."""
import pytest

from apps.learning.pipelines.validate_walk_forward import (
    WalkForwardConfig,
    WalkForwardValidator,
)


class TestLeakageDetection:
    """
    Verify that walk-forward splits never allow future data to leak
    into the training window.
    """

    def test_fold_test_start_after_train_end(self):
        """test_start must always come after train_end in each fold."""
        config = WalkForwardConfig(n_folds=3, min_train_samples=20)
        rows = [{"date": f"2023-{i % 12 + 1:02d}-01", "x": i} for i in range(200)]
        result = WalkForwardValidator(config).validate(rows)

        for fold in result.fold_results:
            assert fold.test_start >= fold.train_end, (
                f"Leakage: fold {fold.fold_index} test_start={fold.test_start} "
                f"before train_end={fold.train_end}"
            )

    def test_fold_index_is_sequential(self):
        config = WalkForwardConfig(n_folds=3, min_train_samples=20)
        rows = [{"date": f"2023-01-{i + 1:02d}", "x": i} for i in range(200)]
        result = WalkForwardValidator(config).validate(rows)
        indices = [f.fold_index for f in result.fold_results]
        assert indices == list(range(len(indices))), "Fold indices must be sequential"

    def test_no_negative_train_samples(self):
        config = WalkForwardConfig(n_folds=2, min_train_samples=20)
        rows = [{"date": "2023-01-01", "x": i} for i in range(200)]
        result = WalkForwardValidator(config).validate(rows)
        for fold in result.fold_results:
            assert fold.n_train > 0

    def test_no_negative_test_samples(self):
        config = WalkForwardConfig(n_folds=2, min_train_samples=20)
        rows = [{"date": "2023-01-01", "x": i} for i in range(200)]
        result = WalkForwardValidator(config).validate(rows)
        for fold in result.fold_results:
            assert fold.n_test > 0
