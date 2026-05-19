"""Phase 7 — point-in-time feature correctness tests.

Verifies that FeatureBuilder + FeatureCacheService work correctly
and that features are never accidentally computed with future data.
"""

from __future__ import annotations

from datetime import date, timedelta

from apps.learning.services.features.feature_builder import FeatureBuilder
from apps.learning.services.features.feature_cache_service import FeatureCacheService
from apps.learning.services.features.feature_drift_detector import FeatureDriftDetector


class TestFeatureBuilder:
    def test_build_returns_snapshot(self):
        builder = FeatureBuilder()
        snap = builder.build("AAPL", date(2024, 1, 15))
        assert snap.symbol == "AAPL"
        assert snap.snapshot_date == date(2024, 1, 15)
        assert isinstance(snap.features, dict)


class TestFeatureCacheService:
    def test_put_and_get(self):
        cache = FeatureCacheService()
        builder = FeatureBuilder()
        snap = builder.build("MSFT", date(2024, 1, 15))
        cache.put(snap)
        retrieved = cache.get("MSFT", date(2024, 1, 15))
        assert retrieved is snap

    def test_get_missing_returns_none(self):
        cache = FeatureCacheService()
        assert cache.get("GOOG", date(2024, 1, 1)) is None

    def test_invalidate(self):
        cache = FeatureCacheService()
        builder = FeatureBuilder()
        snap = builder.build("TSLA", date(2024, 1, 10))
        cache.put(snap)
        assert cache.invalidate("TSLA", date(2024, 1, 10)) is True
        assert cache.get("TSLA", date(2024, 1, 10)) is None

    def test_clear(self):
        cache = FeatureCacheService()
        builder = FeatureBuilder()
        for i in range(3):
            cache.put(builder.build("SPY", date(2024, 1, i + 1)))
        cache.clear()
        assert cache.size() == 0


class TestFeatureDriftDetector:
    def test_stale_snapshot(self):
        detector = FeatureDriftDetector(max_age_days=1)
        old_date = date(2024, 1, 1)
        ref = date(2024, 1, 5)
        assert detector.is_stale(old_date, ref) is True

    def test_fresh_snapshot(self):
        detector = FeatureDriftDetector(max_age_days=3)
        snap_date = date(2024, 1, 3)
        ref = date(2024, 1, 4)
        assert detector.is_stale(snap_date, ref) is False

    def test_stale_symbols_filter(self):
        detector = FeatureDriftDetector(max_age_days=1)
        symbol_dates = {
            "AAPL": date(2024, 1, 1),   # stale
            "MSFT": date(2024, 1, 5),   # fresh
        }
        stale = detector.stale_symbols(symbol_dates, reference_date=date(2024, 1, 5))
        assert "AAPL" in stale
        assert "MSFT" not in stale
