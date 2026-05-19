"""RegimeValidationService — validate regime classification correctness."""

from __future__ import annotations

from apps.learning.services.regime.regime_classifier import RegimeClassifier, RegimeInput


_VALID_REGIMES = frozenset(
    ["risk_on", "risk_off", "high_vol", "low_vol", "chop", "trend"]
)


class RegimeValidationService:
    """Run sanity checks on regime outputs."""

    def __init__(self, classifier: RegimeClassifier | None = None) -> None:
        self._classifier = classifier or RegimeClassifier()

    def validate_output(self, regime: str, confidence: float) -> list[str]:
        """Return a list of validation failure messages (empty = pass)."""
        errors: list[str] = []
        if regime not in _VALID_REGIMES:
            errors.append(f"Unknown regime '{regime}'")
        if not (0.0 <= confidence <= 1.0):
            errors.append(f"Confidence {confidence} outside [0, 1]")
        return errors

    def validate_transition(self, previous: str, current: str) -> list[str]:
        """Check for implausible regime transitions (e.g. low_vol → crisis)."""
        errors: list[str] = []
        disallowed = {
            "low_vol": {"high_vol"},
        }
        if current in disallowed.get(previous, set()):
            errors.append(
                f"Implausible transition {previous} → {current}: "
                "check indicator data quality"
            )
        return errors
