"""ScoreThresholdService — enforce minimum score thresholds before execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThresholdConfig:
    """Per-bucket minimum score thresholds."""

    min_score: float = 0.60
    min_confidence: float = 0.50


class ScoreThresholdService:
    """Apply threshold gates to scored opportunities.

    If a score is below the configured minimum, the opportunity is blocked.
    """

    _DEFAULT = ThresholdConfig()

    def __init__(self, configs: dict[str, ThresholdConfig] | None = None) -> None:
        self._configs: dict[str, ThresholdConfig] = configs or {}

    def passes(self, bucket: str, score: float, confidence: float = 1.0) -> bool:
        """Return True if the score and confidence meet the threshold for *bucket*."""
        cfg = self._configs.get(bucket, self._DEFAULT)
        return score >= cfg.min_score and confidence >= cfg.min_confidence

    def register(self, bucket: str, config: ThresholdConfig) -> None:
        self._configs[bucket] = config
