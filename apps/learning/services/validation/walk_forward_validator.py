"""Walk-forward validator service — time-series cross-validation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.learning.pipelines.validate_walk_forward import (
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardValidator,
)


@dataclass
class WalkForwardReport:
    """Extended walk-forward report with pass/fail determination."""

    result: WalkForwardResult
    gate_passed: bool
    gate_reason: str


class WalkForwardValidatorService:
    """
    Service wrapper around WalkForwardValidator that applies policy gates
    and produces a structured report for the governance pipeline.
    """

    def __init__(self, config: WalkForwardConfig | None = None) -> None:
        self._validator = WalkForwardValidator(config)

    def run(
        self,
        dated_rows: list[dict[str, Any]],
        date_column: str = "date",
        metric_name: str = "auc",
        pass_threshold: float = 0.55,
    ) -> WalkForwardReport:
        """
        Run walk-forward validation and evaluate against policy gates.

        Returns:
            WalkForwardReport with gate_passed and human-readable reason.
        """
        result = self._validator.validate(
            dated_rows,
            date_column=date_column,
            metric_name=metric_name,
            pass_threshold=pass_threshold,
        )

        if result.passed:
            gate_reason = (
                f"Mean {metric_name} {result.mean_metric:.3f} >= "
                f"threshold {pass_threshold:.3f}"
            )
        else:
            gate_reason = (
                f"Mean {metric_name} {result.mean_metric:.3f} < "
                f"threshold {pass_threshold:.3f}"
            )

        return WalkForwardReport(
            result=result,
            gate_passed=result.passed,
            gate_reason=gate_reason,
        )
