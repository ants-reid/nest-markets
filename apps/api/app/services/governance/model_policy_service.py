"""ModelPolicyService — policy enforcement for model promotion decisions.

Encodes the rules from docs/models/model-promotion-policy.md:
- Minimum AUC or accuracy threshold per model type
- Minimum number of walk-forward folds
- Brier score cap for scoring/regime models
- Mandatory shadow comparison before promotion
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromotionPolicy:
    """Configurable thresholds for model promotion approval."""

    # Per model-type minimum primary metric (AUC or accuracy)
    min_primary_metric: dict[str, float] = field(default_factory=lambda: {
        "regime": 0.65,
        "scoring": 0.62,
        "execution": 0.65,
    })
    # Maximum Brier score (lower = better calibration)
    max_brier_score: dict[str, float] = field(default_factory=lambda: {
        "regime": 0.22,
        "scoring": 0.22,
        "execution": 0.25,
    })
    min_walk_forward_folds: int = 3
    require_shadow_comparison: bool = True
    min_shadow_improvement_pct: float = 0.0  # 0 % = must not regress


@dataclass
class PolicyCheckResult:
    """Result of a policy gate check for a single rule."""

    rule: str
    passed: bool
    value: Any
    threshold: Any
    reason: str


@dataclass
class PolicyEvaluation:
    """Aggregated policy evaluation for a model candidate."""

    model_type: str
    checks: list[PolicyCheckResult]
    overall_passed: bool
    summary: str


class ModelPolicyService:
    """
    Evaluates whether a candidate model meets promotion policy gates.

    All gate checks are collected before returning so callers receive a
    complete picture of which rules failed.
    """

    def __init__(self, policy: PromotionPolicy | None = None) -> None:
        self.policy = policy or PromotionPolicy()

    def evaluate(
        self,
        model_type: str,
        metrics: dict[str, float],
        n_walk_forward_folds: int = 0,
        shadow_improvement_pct: float | None = None,
    ) -> PolicyEvaluation:
        """
        Evaluate a candidate against the promotion policy.

        Args:
            model_type: One of ``regime``, ``scoring``, ``execution``.
            metrics: Dict of metric names → values.  Must contain
                ``primary_metric`` (AUC or accuracy).  ``brier_score``
                is checked if present.
            n_walk_forward_folds: Number of WFV folds completed.
            shadow_improvement_pct: Shadow model improvement over active
                (required when ``policy.require_shadow_comparison`` is True).

        Returns:
            PolicyEvaluation with per-rule results and overall gate.

        Raises:
            ValueError: If model_type is not recognised.
        """
        valid = {"regime", "scoring", "execution"}
        if model_type not in valid:
            raise ValueError(
                f"Invalid model_type '{model_type}'. Valid: {sorted(valid)}"
            )

        checks: list[PolicyCheckResult] = []

        # — Primary metric gate —
        primary = metrics.get("primary_metric")
        min_primary = self.policy.min_primary_metric.get(model_type, 0.60)
        checks.append(PolicyCheckResult(
            rule="min_primary_metric",
            passed=primary is not None and primary >= min_primary,
            value=primary,
            threshold=min_primary,
            reason=(
                f"primary_metric {primary} >= {min_primary}"
                if primary is not None and primary >= min_primary
                else f"primary_metric {primary} < {min_primary} (required)"
            ),
        ))

        # — Brier score gate (optional but enforced if present) —
        brier = metrics.get("brier_score")
        max_brier = self.policy.max_brier_score.get(model_type, 0.25)
        if brier is not None:
            checks.append(PolicyCheckResult(
                rule="max_brier_score",
                passed=brier <= max_brier,
                value=brier,
                threshold=max_brier,
                reason=(
                    f"brier_score {brier} <= {max_brier}"
                    if brier <= max_brier
                    else f"brier_score {brier} > {max_brier} (too poor calibration)"
                ),
            ))

        # — Walk-forward folds gate —
        checks.append(PolicyCheckResult(
            rule="min_walk_forward_folds",
            passed=n_walk_forward_folds >= self.policy.min_walk_forward_folds,
            value=n_walk_forward_folds,
            threshold=self.policy.min_walk_forward_folds,
            reason=(
                f"{n_walk_forward_folds} folds >= {self.policy.min_walk_forward_folds}"
                if n_walk_forward_folds >= self.policy.min_walk_forward_folds
                else f"Only {n_walk_forward_folds} folds completed, need {self.policy.min_walk_forward_folds}"
            ),
        ))

        # — Shadow comparison gate —
        if self.policy.require_shadow_comparison:
            shadow_ok = (
                shadow_improvement_pct is not None
                and shadow_improvement_pct >= self.policy.min_shadow_improvement_pct
            )
            checks.append(PolicyCheckResult(
                rule="shadow_comparison",
                passed=shadow_ok,
                value=shadow_improvement_pct,
                threshold=self.policy.min_shadow_improvement_pct,
                reason=(
                    f"Shadow improvement {shadow_improvement_pct:.1%} >= "
                    f"{self.policy.min_shadow_improvement_pct:.1%}"
                    if shadow_ok
                    else "Shadow comparison required but not provided or below threshold"
                ),
            ))

        overall_passed = all(c.passed for c in checks)
        failed = [c.rule for c in checks if not c.passed]
        summary = (
            "All policy gates passed"
            if overall_passed
            else f"Failed gates: {', '.join(failed)}"
        )

        return PolicyEvaluation(
            model_type=model_type,
            checks=checks,
            overall_passed=overall_passed,
            summary=summary,
        )
