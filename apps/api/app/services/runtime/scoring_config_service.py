"""ScoringConfigService — loads and manages composite scoring weights.

Scoring weights define how signal quality metrics are combined into a
single composite score (0–100).  The default weights match the Phase 1
formula:

    composite = 0.40 * signal_score
              + 0.30 * confidence
              + 0.10 * catalyst_score
              + 0.20 * historical_win_rate

Config is sourced from environment / app settings.  A future DB-backed
override layer can be added by implementing ``ScoringConfigService``
against a ``scoring_configs`` table once the Phase 4 data model is in place.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    """Composite scoring weight configuration."""

    signal_score: float = 0.40
    confidence: float = 0.30
    catalyst_score: float = 0.10
    historical_win_rate: float = 0.20

    def validate(self) -> None:
        """Raise ValueError if weights don't sum to 1.0 (within tolerance)."""
        total = self.signal_score + self.confidence + self.catalyst_score + self.historical_win_rate
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"ScoringWeights must sum to 1.0; got {total:.6f}")


# Singleton default weights — used when no DB override is active
DEFAULT_WEIGHTS = ScoringWeights()


class ScoringConfigService:
    """Manages scoring weight configuration.

    Phase 3: returns hardcoded defaults.  Phase 8 will extend this to load
    active weights from the ``scoring_configs`` DB table.
    """

    def get_active_weights(self) -> ScoringWeights:
        """Return the currently active scoring weights."""
        return DEFAULT_WEIGHTS

    def build_weights(
        self,
        *,
        signal_score: float = 0.40,
        confidence: float = 0.30,
        catalyst_score: float = 0.10,
        historical_win_rate: float = 0.20,
    ) -> ScoringWeights:
        """Construct and validate a custom weight set."""
        weights = ScoringWeights(
            signal_score=signal_score,
            confidence=confidence,
            catalyst_score=catalyst_score,
            historical_win_rate=historical_win_rate,
        )
        weights.validate()
        return weights
