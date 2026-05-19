"""Train execution quality model from labeled fill records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionTrainConfig:
    """Configuration for execution model training."""

    min_samples: int = 500
    test_split: float = 0.20
    random_seed: int = 42
    target_column: str = "grade"
    feature_columns: list[str] = field(default_factory=lambda: [
        "spread_pct",
        "liquidity_score",
        "time_of_day_bucket",
        "volume_ratio",
        "volatility_regime",
    ])


@dataclass
class ExecutionTrainResult:
    """Result of an execution model training run."""

    model_id: str
    n_samples: int
    train_accuracy: float
    test_accuracy: float
    grade_distribution: dict[str, int]
    feature_importances: dict[str, float]
    artifacts: dict[str, Any] = field(default_factory=dict)


class ExecutionModelTrainer:
    """
    Trains an execution quality classifier.

    Stub implementation — validates inputs and returns deterministic metrics.
    """

    def __init__(self, config: ExecutionTrainConfig | None = None) -> None:
        self.config = config or ExecutionTrainConfig()

    def train(self, feature_rows: list[dict[str, Any]]) -> ExecutionTrainResult:
        """
        Train an execution quality model.

        Args:
            feature_rows: List of feature dicts with ``target_column`` labels.

        Returns:
            ExecutionTrainResult with evaluation metrics.

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

        grade_distribution: dict[str, int] = {}
        for row in feature_rows:
            g = str(row[self.config.target_column])
            grade_distribution[g] = grade_distribution.get(g, 0) + 1

        return ExecutionTrainResult(
            model_id="execution-model-stub",
            n_samples=len(feature_rows),
            train_accuracy=0.74,
            test_accuracy=0.70,
            grade_distribution=grade_distribution,
            feature_importances={col: 1.0 / len(self.config.feature_columns)
                                  for col in self.config.feature_columns},
        )
