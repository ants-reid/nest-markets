"""ScoreExplainer — produce human-readable explanations for scored opportunities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreExplanation:
    """Breakdown of how a final score was computed."""

    final_score: float
    component_scores: dict[str, float]
    component_weights: dict[str, float]
    dominant_factor: str
    narrative: str


class ScoreExplainer:
    """Explain how component scores contribute to the final weighted score."""

    def explain(
        self,
        component_scores: dict[str, float],
        weights: dict[str, float],
    ) -> ScoreExplanation:
        """Compute final score and return a full explanation."""
        final = sum(
            component_scores.get(k, 0.0) * w for k, w in weights.items()
        )
        dominant = max(weights, key=lambda k: weights[k] * component_scores.get(k, 0.0))
        parts = [
            f"{k}={component_scores.get(k, 0):.2f}×{w:.0%}"
            for k, w in sorted(weights.items())
        ]
        narrative = f"Score {final:.3f}: {', '.join(parts)}; dominant={dominant}"
        return ScoreExplanation(
            final_score=final,
            component_scores=component_scores,
            component_weights=weights,
            dominant_factor=dominant,
            narrative=narrative,
        )
