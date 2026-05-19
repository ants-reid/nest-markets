"""RegimeSnapshotService — capture and store point-in-time regime snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.learning.services.regime.regime_classifier import RegimeClassifier, RegimeInput, RegimeOutput


@dataclass(frozen=True)
class RegimeSnapshot:
    """A dated regime observation."""

    snapshot_date: date
    regime: str
    confidence: float
    reason: str


class RegimeSnapshotService:
    """Create and manage point-in-time regime snapshots."""

    def __init__(self, classifier: RegimeClassifier | None = None) -> None:
        self._classifier = classifier or RegimeClassifier()
        self._history: list[RegimeSnapshot] = []

    def capture(self, inputs: RegimeInput, snapshot_date: date | None = None) -> RegimeSnapshot:
        """Classify and record a new regime snapshot."""
        result: RegimeOutput = self._classifier.classify(inputs)
        snap = RegimeSnapshot(
            snapshot_date=snapshot_date or date.today(),
            regime=result.regime,
            confidence=result.confidence,
            reason=result.reason,
        )
        self._history.append(snap)
        return snap

    def latest(self) -> RegimeSnapshot | None:
        """Return the most recently captured snapshot."""
        return self._history[-1] if self._history else None

    def history(self) -> list[RegimeSnapshot]:
        """Return all captured snapshots in chronological order."""
        return list(self._history)
