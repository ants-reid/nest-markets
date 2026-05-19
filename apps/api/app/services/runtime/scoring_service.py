"""ScoringService — composite scoring computation decoupled from signal generation.

This service owns the scoring formula and is the single source of truth for
how ``signal_score``, ``confidence``, ``catalyst_score``, and historical win
rate are combined into a composite ranking score (0–100).

Extracting this logic from ``OpportunityRankerService`` and ``SignalService``
enables:
- Config-driven weight adjustments (Phase 8)
- Regime-aware weight overrides (Phase 8)
- Consistent scoring across ranking and signal evaluation
"""

from __future__ import annotations

from .scoring_config_service import ScoringConfigService, ScoringWeights

# Neutral prior used when insufficient outcome history exists
_NEUTRAL_WIN_RATE = 0.50

# Minimum signal_score to be ranked (filters should_trade=False proxies)
MIN_SIGNAL_SCORE = 50.0


class ScoringService:
    """Computes composite ranking scores for signals.

    All callers (OpportunityRankerService, scoring routes) should delegate
    score computation here rather than embedding the formula inline.
    """

    def __init__(self, config_service: ScoringConfigService | None = None) -> None:
        self._config = config_service or ScoringConfigService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def composite_score(
        self,
        *,
        signal_score: float,
        confidence: float,
        catalyst_score: float,
        historical_win_rate: float = _NEUTRAL_WIN_RATE,
        weights: ScoringWeights | None = None,
    ) -> float:
        """Return composite ranking score in [0, 100].

        Args:
            signal_score: Raw signal score from LLM (0–100).
            confidence: Model confidence (0–1).
            catalyst_score: Catalyst strength (0–1).
            historical_win_rate: Setup × regime win rate (0–1).
                Defaults to the neutral prior (0.50) when there is
                insufficient history.
            weights: Override the active config weights for this call.
                If None, uses the active weight config.

        Returns:
            Composite score in [0, 100].
        """
        w = weights or self._config.get_active_weights()

        # Normalise signal_score from 0-100 to 0-1 for weighted sum
        s_norm = _clamp(signal_score, 0.0, 100.0) / 100.0
        c_norm = _clamp(confidence, 0.0, 1.0)
        cat_norm = _clamp(catalyst_score, 0.0, 1.0)
        hist_norm = _clamp(historical_win_rate, 0.0, 1.0)

        raw = (
            w.signal_score * s_norm
            + w.confidence * c_norm
            + w.catalyst_score * cat_norm
            + w.historical_win_rate * hist_norm
        )
        return round(_clamp(raw * 100.0, 0.0, 100.0), 4)

    def is_tradeable(self, signal_score: float) -> bool:
        """Return True if the signal meets the minimum score threshold."""
        return signal_score >= MIN_SIGNAL_SCORE

    def explain(
        self,
        *,
        signal_score: float,
        confidence: float,
        catalyst_score: float,
        historical_win_rate: float = _NEUTRAL_WIN_RATE,
        weights: ScoringWeights | None = None,
    ) -> dict:
        """Return a breakdown dict explaining how each component contributes.

        Useful for the ``GET /scoring/explain/{signal_id}`` endpoint.
        """
        w = weights or self._config.get_active_weights()
        s_norm = _clamp(signal_score, 0.0, 100.0) / 100.0
        c_norm = _clamp(confidence, 0.0, 1.0)
        cat_norm = _clamp(catalyst_score, 0.0, 1.0)
        hist_norm = _clamp(historical_win_rate, 0.0, 1.0)

        contributions = {
            "signal_score": round(w.signal_score * s_norm * 100.0, 4),
            "confidence": round(w.confidence * c_norm * 100.0, 4),
            "catalyst_score": round(w.catalyst_score * cat_norm * 100.0, 4),
            "historical_win_rate": round(w.historical_win_rate * hist_norm * 100.0, 4),
        }
        total = sum(contributions.values())
        return {
            "composite_score": round(_clamp(total, 0.0, 100.0), 4),
            "contributions": contributions,
            "weights": {
                "signal_score": w.signal_score,
                "confidence": w.confidence,
                "catalyst_score": w.catalyst_score,
                "historical_win_rate": w.historical_win_rate,
            },
            "inputs": {
                "signal_score": signal_score,
                "confidence": confidence,
                "catalyst_score": catalyst_score,
                "historical_win_rate": historical_win_rate,
            },
        }


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
