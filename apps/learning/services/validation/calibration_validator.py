"""Calibration validator — verify model probability outputs are well-calibrated."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CalibrationBucket:
    """Statistics for one probability bucket."""

    bucket_low: float
    bucket_high: float
    mean_predicted: float
    mean_actual: float
    n_samples: int
    error: float  # |mean_predicted - mean_actual|


@dataclass
class CalibrationValidationResult:
    """Result of calibration validation."""

    model_id: str
    n_samples: int
    mean_calibration_error: float
    max_calibration_error: float
    brier_score: float
    buckets: list[CalibrationBucket]
    passed: bool
    reason: str


class CalibrationValidator:
    """
    Validates that a model's probability outputs are well-calibrated.

    Uses equal-width buckets to compare predicted probabilities against
    actual outcome rates.
    """

    def __init__(
        self,
        n_buckets: int = 10,
        max_calibration_error: float = 0.10,
        max_brier_score: float = 0.25,
    ) -> None:
        self.n_buckets = n_buckets
        self.max_calibration_error = max_calibration_error
        self.max_brier_score = max_brier_score

    def validate(
        self,
        model_id: str,
        predictions: list[float],
        actuals: list[float],
    ) -> CalibrationValidationResult:
        """
        Validate calibration of model probability outputs.

        Args:
            model_id: Identifier for the model being validated.
            predictions: List of predicted probabilities in [0, 1].
            actuals: List of binary outcomes (0 or 1).

        Returns:
            CalibrationValidationResult.

        Raises:
            ValueError: If predictions and actuals have mismatched lengths
                or are empty.
        """
        if len(predictions) != len(actuals):
            raise ValueError(
                f"predictions ({len(predictions)}) and actuals ({len(actuals)}) "
                "must have the same length"
            )
        if not predictions:
            raise ValueError("predictions list must not be empty")

        bucket_size = 1.0 / self.n_buckets
        buckets: list[CalibrationBucket] = []

        for i in range(self.n_buckets):
            low = i * bucket_size
            high = (i + 1) * bucket_size
            indices = [
                j for j, p in enumerate(predictions)
                if low <= p < high or (i == self.n_buckets - 1 and p == 1.0)
            ]
            if not indices:
                continue

            mean_pred = sum(predictions[j] for j in indices) / len(indices)
            mean_act = sum(actuals[j] for j in indices) / len(indices)
            buckets.append(CalibrationBucket(
                bucket_low=low,
                bucket_high=high,
                mean_predicted=mean_pred,
                mean_actual=mean_act,
                n_samples=len(indices),
                error=abs(mean_pred - mean_act),
            ))

        if not buckets:
            # All predictions in same bucket — minimal test
            mean_pred = sum(predictions) / len(predictions)
            mean_act = sum(actuals) / len(actuals)
            buckets.append(CalibrationBucket(
                bucket_low=0.0, bucket_high=1.0,
                mean_predicted=mean_pred, mean_actual=mean_act,
                n_samples=len(predictions), error=abs(mean_pred - mean_act),
            ))

        errors = [b.error for b in buckets]
        mean_cal_error = sum(errors) / len(errors)
        max_cal_error = max(errors)

        n = len(predictions)
        brier_score = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / n

        passed = (
            max_cal_error <= self.max_calibration_error
            and brier_score <= self.max_brier_score
        )
        if passed:
            reason = f"Calibration OK: MCE={mean_cal_error:.3f}, Brier={brier_score:.3f}"
        else:
            reason = (
                f"Calibration FAILED: MCE={mean_cal_error:.3f} "
                f"(max allowed {self.max_calibration_error}), "
                f"Brier={brier_score:.3f} (max allowed {self.max_brier_score})"
            )

        return CalibrationValidationResult(
            model_id=model_id,
            n_samples=n,
            mean_calibration_error=mean_cal_error,
            max_calibration_error=max_cal_error,
            brier_score=brier_score,
            buckets=buckets,
            passed=passed,
            reason=reason,
        )
