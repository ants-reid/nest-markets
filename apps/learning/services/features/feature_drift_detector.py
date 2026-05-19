"""FeatureDriftDetector — detect stale or drifted feature values."""

from __future__ import annotations

from datetime import date, timedelta


class FeatureDriftDetector:
    """Detect features that are too old or have drifted beyond acceptable bounds.

    Phase 7 stub: staleness-check only.  Statistical drift detection will
    be added when training data is available.
    """

    def __init__(self, max_age_days: int = 1) -> None:
        self._max_age = timedelta(days=max_age_days)

    def is_stale(self, snapshot_date: date, reference_date: date | None = None) -> bool:
        """Return True if the snapshot is older than *max_age_days*."""
        ref = reference_date or date.today()
        return (ref - snapshot_date) > self._max_age

    def stale_symbols(
        self,
        symbol_dates: dict[str, date],
        reference_date: date | None = None,
    ) -> list[str]:
        """Return symbols whose latest snapshot is stale."""
        return [
            symbol
            for symbol, snap_date in symbol_dates.items()
            if self.is_stale(snap_date, reference_date)
        ]
