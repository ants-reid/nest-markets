"""ScoreResolver — resolve the active scoring model configuration.

Reads from the score_model_registry to find the currently ACTIVE model
for a given asset/strategy/timeframe bucket.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringConfig:
    """Active scoring model descriptor."""

    model_id: str
    model_version: str
    bucket: str  # e.g. "equity/momentum/1D"
    weights: dict[str, float]


class ScoreResolver:
    """Resolve the active ScoringConfig for a given bucket.

    Phase 8 stub: returns a hardcoded default config.
    Full implementation queries the score_model_registry table.
    """

    _DEFAULT_WEIGHTS: dict[str, float] = {
        "momentum": 0.40,
        "risk": 0.30,
        "news": 0.10,
        "execution": 0.20,
    }

    def resolve(self, bucket: str) -> ScoringConfig:
        """Return the active ScoringConfig for *bucket*."""
        return ScoringConfig(
            model_id="default-v1",
            model_version="1.0.0",
            bucket=bucket,
            weights=self._DEFAULT_WEIGHTS,
        )
