"""Shadow model comparison service — candidate vs active evaluation."""
from __future__ import annotations

from dataclasses import dataclass

from apps.learning.pipelines.compare_shadow_vs_active import (
    ModelPrediction,
    ShadowCompareConfig,
    ShadowCompareResult,
    ShadowCompareService,
)


@dataclass
class ShadowCompareReport:
    """Report wrapping shadow comparison result with governance context."""

    result: ShadowCompareResult
    promote_eligible: bool
    summary: str


class ShadowModelCompareService:
    """
    Service wrapper around ShadowCompareService that attaches governance
    context and produces an actionable report.
    """

    def __init__(self, config: ShadowCompareConfig | None = None) -> None:
        self._service = ShadowCompareService(config)

    def compare_and_report(
        self,
        active_predictions: list[ModelPrediction],
        shadow_predictions: list[ModelPrediction],
    ) -> ShadowCompareReport:
        """
        Compare shadow vs active and produce a governance report.

        Returns:
            ShadowCompareReport with promotion eligibility determination.
        """
        result = self._service.compare(active_predictions, shadow_predictions)

        promote_eligible = result.recommendation == "promote"
        summary = (
            f"Shadow {result.config.metric_name}: {result.shadow_metric:.4f} "
            f"vs active: {result.active_metric:.4f} "
            f"(delta: {result.delta:+.4f}, {result.improvement_pct:+.1%}). "
            f"Recommendation: {result.recommendation.upper()}"
        )

        return ShadowCompareReport(
            result=result,
            promote_eligible=promote_eligible,
            summary=summary,
        )
