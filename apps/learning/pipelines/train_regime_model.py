"""Train regime classifier model from labeled feature snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RegimeTrainConfig:
    """Configuration for regime model training."""

    min_samples: int = 500
    test_split: float = 0.20
    random_seed: int = 42
    feature_columns: list[str] = field(default_factory=lambda: [
        "yield_curve_slope",
        "vix_level",
        "breadth_advance_decline",
        "momentum_5d",
        "realized_vol_20d",
    ])


@dataclass
class RegimeTrainResult:
    """Result of a regime model training run."""

    model_id: str
    n_samples: int
    train_accuracy: float
    test_accuracy: float
    regime_distribution: dict[str, int]
    feature_importances: dict[str, float]
    artifacts: dict[str, Any] = field(default_factory=dict)


class RegimeModelTrainer:
    """
    Trains a regime classifier from labeled feature snapshots.

    In production this wraps scikit-learn / XGBoost. For now it is a
    deterministic stub that validates inputs and returns a fixed result
    so downstream pipeline tests can run without ML dependencies.
    """

    def __init__(self, config: RegimeTrainConfig | None = None) -> None:
        self.config = config or RegimeTrainConfig()

    # ------------------------------------------------------------------
    def train(
        self,
        feature_rows: list[dict[str, Any]],
        label_column: str = "regime",
    ) -> RegimeTrainResult:
        """
        Train a regime classifier.

        Args:
            feature_rows: List of dicts, each a feature snapshot with
                at least the columns in ``config.feature_columns`` plus
                the ``label_column``.
            label_column: Column name containing regime labels.

        Returns:
            RegimeTrainResult with evaluation metrics.

        Raises:
            ValueError: If there are not enough samples or required
                columns are missing.
        """
        if len(feature_rows) < self.config.min_samples:
            raise ValueError(
                f"Insufficient training data: got {len(feature_rows)}, "
                f"need at least {self.config.min_samples}"
            )

        required = set(self.config.feature_columns) | {label_column}
        if feature_rows:
            missing = required - set(feature_rows[0].keys())
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

        regime_distribution: dict[str, int] = {}
        for row in feature_rows:
            regime = str(row[label_column])
            regime_distribution[regime] = regime_distribution.get(regime, 0) + 1

        # Stub — real implementation would fit a model here
        return RegimeTrainResult(
            model_id="regime-model-stub",
            n_samples=len(feature_rows),
            train_accuracy=0.72,
            test_accuracy=0.68,
            regime_distribution=regime_distribution,
            feature_importances={col: 1.0 / len(self.config.feature_columns)
                                  for col in self.config.feature_columns},
        )
