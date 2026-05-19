"""DNTProbabilityService — estimate the probability of a Do-Not-Trade outcome."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DNTInput:
    """Inputs used to compute do-not-trade probability."""

    score: float                     # opportunity score 0–1
    vix: float                       # current VIX
    regime: str                      # current market regime
    days_to_event: int | None = None  # days to next scheduled event


class DNTProbabilityService:
    """Estimate the probability that an opportunity should NOT be traded.

    Higher DNT probability → reduce or skip the trade.
    The Phase 8 implementation uses a simple rules-based heuristic;
    a calibrated ML model will replace this in Phase 10.
    """

    def estimate(self, inputs: DNTInput) -> float:
        """Return DNT probability in [0, 1]."""
        base = 1.0 - inputs.score  # low scores have higher DNT base

        # VIX penalty
        if inputs.vix >= 30:
            base = min(1.0, base + 0.25)
        elif inputs.vix >= 20:
            base = min(1.0, base + 0.10)

        # regime penalty
        if inputs.regime in {"high_vol", "risk_off"}:
            base = min(1.0, base + 0.15)

        # event proximity penalty
        if inputs.days_to_event is not None and 0 <= inputs.days_to_event <= 1:
            base = min(1.0, base + 0.10)

        return round(base, 4)
