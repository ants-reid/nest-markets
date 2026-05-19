"""FeatureCacheService — in-memory cache for computed feature snapshots."""

from __future__ import annotations

from datetime import date

from apps.learning.services.features.feature_builder import FeatureSnapshot


class FeatureCacheService:
    """LRU-style in-memory cache for FeatureSnapshot objects.

    Keyed by (symbol, snapshot_date).
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, date], FeatureSnapshot] = {}

    def get(self, symbol: str, snapshot_date: date) -> FeatureSnapshot | None:
        return self._cache.get((symbol, snapshot_date))

    def put(self, snapshot: FeatureSnapshot) -> None:
        self._cache[(snapshot.symbol, snapshot.snapshot_date)] = snapshot

    def invalidate(self, symbol: str, snapshot_date: date) -> bool:
        key = (symbol, snapshot_date)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)
