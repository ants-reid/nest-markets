"""Tests for training pipeline reproducibility (Phase 10)."""
from apps.learning.pipelines.train_regime_model import (
    RegimeModelTrainer,
    RegimeTrainConfig,
)
from apps.learning.pipelines.train_scoring_model import (
    ScoringModelTrainer,
    ScoringTrainConfig,
)
from apps.learning.pipelines.train_execution_model import (
    ExecutionModelTrainer,
    ExecutionTrainConfig,
)
from apps.learning.pipelines.publish_candidate_model import (
    CandidateModelPublisher,
    PublishRequest,
)


def _regime_rows(n: int) -> list[dict]:
    cols = ["yield_curve_slope", "vix_level", "breadth_advance_decline",
            "momentum_5d", "realized_vol_20d"]
    return [{c: float(i) for c in cols} | {"regime": "risk_on"} for i in range(n)]


def _scoring_rows(n: int) -> list[dict]:
    cols = ["momentum_score", "risk_score", "news_score", "execution_score", "regime"]
    return [{c: 0.5 for c in cols} | {"hit": 1} for _ in range(n)]


def _execution_rows(n: int) -> list[dict]:
    cols = ["spread_pct", "liquidity_score", "time_of_day_bucket",
            "volume_ratio", "volatility_regime"]
    return [{c: 0.5 for c in cols} | {"grade": "good"} for _ in range(n)]


class TestReproducibility:
    def test_regime_trainer_is_deterministic(self):
        config = RegimeTrainConfig(random_seed=42, min_samples=50)
        rows = _regime_rows(100)
        r1 = RegimeModelTrainer(config).train(rows)
        r2 = RegimeModelTrainer(config).train(rows)
        assert r1.train_accuracy == r2.train_accuracy
        assert r1.test_accuracy == r2.test_accuracy

    def test_scoring_trainer_is_deterministic(self):
        config = ScoringTrainConfig(random_seed=42, min_samples=50)
        rows = _scoring_rows(100)
        r1 = ScoringModelTrainer(config).train(rows)
        r2 = ScoringModelTrainer(config).train(rows)
        assert r1.train_auc == r2.train_auc
        assert r1.brier_score == r2.brier_score

    def test_execution_trainer_is_deterministic(self):
        config = ExecutionTrainConfig(random_seed=42, min_samples=50)
        rows = _execution_rows(100)
        r1 = ExecutionModelTrainer(config).train(rows)
        r2 = ExecutionModelTrainer(config).train(rows)
        assert r1.train_accuracy == r2.train_accuracy
        assert r1.test_accuracy == r2.test_accuracy

    def test_publish_candidate_same_id_for_same_request(self):
        publisher = CandidateModelPublisher()
        req = PublishRequest(
            model_type="regime",
            model_id="v1",
            artifacts={"weights": [0.1, 0.2]},
            metrics={"auc": 0.70},
            training_config={"seed": 42},
        )
        r1 = publisher.publish(req)
        r2 = publisher.publish(req)
        assert r1.candidate_id == r2.candidate_id

    def test_publish_invalid_model_type_raises(self):
        import pytest
        publisher = CandidateModelPublisher()
        with pytest.raises(ValueError, match="Invalid model_type"):
            publisher.publish(PublishRequest(
                model_type="unknown",
                model_id="v1",
                artifacts={"w": 1},
                metrics={"auc": 0.6},
                training_config={},
            ))

    def test_regime_trainer_raises_on_insufficient_data(self):
        import pytest
        trainer = RegimeModelTrainer(RegimeTrainConfig(min_samples=500))
        with pytest.raises(ValueError, match="Insufficient training data"):
            trainer.train(_regime_rows(10))

    def test_scoring_trainer_raises_on_missing_columns(self):
        import pytest
        trainer = ScoringModelTrainer(ScoringTrainConfig(min_samples=50))
        rows = [{"wrong_col": 0.5, "hit": 1} for _ in range(100)]
        with pytest.raises(ValueError, match="Missing required columns"):
            trainer.train(rows)
