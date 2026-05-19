"""Sample size policy service — enforce minimum data gates before training."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SampleSizePolicy:
    """Minimum sample counts for each model type."""

    regime_model: int = 500
    scoring_model: int = 1000
    execution_model: int = 500
    walk_forward_per_fold: int = 200


@dataclass
class SampleSizeCheckResult:
    """Result of a sample size gate check."""

    model_type: str
    n_samples: int
    required: int
    passed: bool
    reason: str


class SampleSizePolicyService:
    """
    Enforces minimum sample size gates before training is allowed.

    Prevents models from being trained on insufficient data which would
    produce unreliable performance estimates.
    """

    def __init__(self, policy: SampleSizePolicy | None = None) -> None:
        self.policy = policy or SampleSizePolicy()

    def check(self, model_type: str, n_samples: int) -> SampleSizeCheckResult:
        """
        Check if there are enough samples to train a model.

        Args:
            model_type: One of ``regime_model``, ``scoring_model``,
                ``execution_model``, or ``walk_forward_per_fold``.
            n_samples: Number of labeled samples available.

        Returns:
            SampleSizeCheckResult with pass/fail and reason.

        Raises:
            ValueError: If model_type is not recognised.
        """
        thresholds = {
            "regime_model": self.policy.regime_model,
            "scoring_model": self.policy.scoring_model,
            "execution_model": self.policy.execution_model,
            "walk_forward_per_fold": self.policy.walk_forward_per_fold,
        }

        if model_type not in thresholds:
            raise ValueError(
                f"Unknown model_type '{model_type}'. "
                f"Valid: {sorted(thresholds)}"
            )

        required = thresholds[model_type]
        passed = n_samples >= required
        reason = (
            f"Have {n_samples} samples, need {required} for {model_type}"
            if not passed
            else f"Sample gate passed: {n_samples} >= {required}"
        )

        return SampleSizeCheckResult(
            model_type=model_type,
            n_samples=n_samples,
            required=required,
            passed=passed,
            reason=reason,
        )

    def check_all(self, counts: dict[str, int]) -> list[SampleSizeCheckResult]:
        """
        Run sample size checks for multiple model types.

        Args:
            counts: Dict mapping model_type → n_samples.

        Returns:
            List of SampleSizeCheckResult, one per model_type.
        """
        return [self.check(mt, n) for mt, n in counts.items()]
