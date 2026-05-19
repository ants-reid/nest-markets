"""ScoreCalibrationService — compute calibration metrics for a scoring model."""

from __future__ import annotations

import math
from typing import Sequence


def _brier_score(predicted: Sequence[float], actual: Sequence[float]) -> float:
    """Mean squared error between predicted probabilities and outcomes."""
    if len(predicted) != len(actual) or not predicted:
        raise ValueError("predicted and actual must be non-empty sequences of equal length")
    return sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(predicted)


def _log_loss(predicted: Sequence[float], actual: Sequence[float], eps: float = 1e-7) -> float:
    total = 0.0
    for p, a in zip(predicted, actual):
        p_clipped = max(eps, min(1 - eps, p))
        total += a * math.log(p_clipped) + (1 - a) * math.log(1 - p_clipped)
    return -total / len(predicted)


class ScoreCalibrationService:
    """Compute calibration metrics comparing predicted scores to outcomes."""

    def brier_score(
        self,
        predicted: Sequence[float],
        actual: Sequence[float],
    ) -> float:
        """Lower is better (0 = perfect)."""
        return _brier_score(predicted, actual)

    def log_loss(
        self,
        predicted: Sequence[float],
        actual: Sequence[float],
    ) -> float:
        """Lower is better."""
        return _log_loss(predicted, actual)

    def calibration_summary(
        self,
        predicted: Sequence[float],
        actual: Sequence[float],
    ) -> dict[str, float]:
        return {
            "brier_score": self.brier_score(predicted, actual),
            "log_loss": self.log_loss(predicted, actual),
            "mean_predicted": sum(predicted) / len(predicted),
            "mean_actual": sum(actual) / len(actual),
            "n": float(len(predicted)),
        }
