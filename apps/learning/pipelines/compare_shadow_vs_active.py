"""Compare shadow (candidate) model predictions against active model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ShadowCompareConfig:
    """Configuration for shadow vs active comparison."""

    min_shadow_records: int = 100
    improvement_threshold: float = 0.02
    metric_name: str = "auc"


@dataclass
class ModelPrediction:
    """A prediction from either shadow or active model."""

    opportunity_id: str
    score: float
    outcome: float | None = None


@dataclass
class ShadowCompareResult:
    """Result of comparing shadow against active model."""

    n_records: int
    active_metric: float
    shadow_metric: float
    delta: float
    improvement_pct: float
    recommendation: str  # "promote" | "hold" | "rollback"
    config: ShadowCompareConfig


class ShadowCompareService:
    """
    Compares candidate (shadow) model against active model on the same
    opportunities to determine if promotion is warranted.
    """

    def __init__(self, config: ShadowCompareConfig | None = None) -> None:
        self.config = config or ShadowCompareConfig()

    def compare(
        self,
        active_predictions: list[ModelPrediction],
        shadow_predictions: list[ModelPrediction],
    ) -> ShadowCompareResult:
        """
        Compare active and shadow model predictions.

        Args:
            active_predictions: Scored opportunities from the active model.
            shadow_predictions: Scored opportunities from the shadow model.
                Must contain the same opportunity IDs as active_predictions.

        Returns:
            ShadowCompareResult with recommendation.

        Raises:
            ValueError: If record counts are mismatched or insufficient.
        """
        if len(active_predictions) != len(shadow_predictions):
            raise ValueError(
                f"Active ({len(active_predictions)}) and shadow "
                f"({len(shadow_predictions)}) prediction counts must match"
            )

        if len(shadow_predictions) < self.config.min_shadow_records:
            raise ValueError(
                f"Insufficient shadow records: got {len(shadow_predictions)}, "
                f"need at least {self.config.min_shadow_records}"
            )

        # Validate IDs match
        active_ids = {p.opportunity_id for p in active_predictions}
        shadow_ids = {p.opportunity_id for p in shadow_predictions}
        if active_ids != shadow_ids:
            raise ValueError("Active and shadow predictions have mismatched opportunity IDs")

        # Stub metric computation (real impl uses sklearn.metrics.roc_auc_score)
        active_metric = self._compute_stub_metric(active_predictions)
        shadow_metric = self._compute_stub_metric(shadow_predictions)

        delta = shadow_metric - active_metric
        improvement_pct = delta / active_metric if active_metric > 0 else 0.0

        if improvement_pct >= self.config.improvement_threshold:
            recommendation = "promote"
        elif improvement_pct < -self.config.improvement_threshold:
            recommendation = "rollback"
        else:
            recommendation = "hold"

        return ShadowCompareResult(
            n_records=len(active_predictions),
            active_metric=active_metric,
            shadow_metric=shadow_metric,
            delta=delta,
            improvement_pct=improvement_pct,
            recommendation=recommendation,
            config=self.config,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _compute_stub_metric(predictions: list[ModelPrediction]) -> float:
        """Stub: return average score of records that have outcomes."""
        scored = [p for p in predictions if p.outcome is not None]
        if not scored:
            return 0.60
        return sum(p.score for p in scored) / len(scored)
