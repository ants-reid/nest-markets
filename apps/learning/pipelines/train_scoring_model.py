"""Train scoring model from labeled opportunity outcomes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoringTrainConfig:
    """Configuration for scoring model training."""

    min_samples: int = 1000
    test_split: float = 0.20
    random_seed: int = 42
    target_column: str = "hit"
    feature_columns: list[str] = field(default_factory=lambda: [
        "momentum_score",
        "risk_score",
        "news_score",
        "execution_score",
        "regime",
    ])


@dataclass
class ScoringTrainResult:
    """Result of a scoring model training run."""

    model_id: str
    n_samples: int
    train_auc: float
    test_auc: float
    brier_score: float
    feature_importances: dict[str, float]
    artifacts: dict[str, Any] = field(default_factory=dict)


class ScoringModelTrainer:
    """
    Trains a calibrated probability model on opportunity outcomes.

    Stub implementation — validates inputs and returns deterministic metrics.
    Real implementation wraps LightGBM / isotonic calibration.
    """

    def __init__(self, config: ScoringTrainConfig | None = None) -> None:
        self.config = config or ScoringTrainConfig()

    def train(self, feature_rows: list[dict[str, Any]]) -> ScoringTrainResult:
        """
        Train a scoring model.

        Args:
            feature_rows: List of dicts containing feature columns and
                the configured ``target_column``.

        Returns:
            ScoringTrainResult with evaluation metrics.

        Raises:
            ValueError: If there are not enough samples or required
                columns are missing.
        """
        if len(feature_rows) < self.config.min_samples:
            raise ValueError(
                f"Insufficient training data: got {len(feature_rows)}, "
                f"need at least {self.config.min_samples}"
            )

        required = set(self.config.feature_columns) | {self.config.target_column}
        if feature_rows:
            missing = required - set(feature_rows[0].keys())
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

        # Stub — real implementation fits a model here
        return ScoringTrainResult(
            model_id="scoring-model-stub",
            n_samples=len(feature_rows),
            train_auc=0.71,
            test_auc=0.67,
            brier_score=0.18,
            feature_importances={col: 1.0 / len(self.config.feature_columns)
                                  for col in self.config.feature_columns},
        )
