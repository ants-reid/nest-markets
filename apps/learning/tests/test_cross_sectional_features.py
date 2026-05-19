"""Phase 7 — cross-sectional feature tests."""

from __future__ import annotations

import pytest

from apps.learning.features.cross_sectional.sector_strength import sector_relative_strength
from apps.learning.features.cross_sectional.breadth import advance_decline_ratio, breadth_thrust
from apps.learning.features.cross_sectional.relative_rank import percentile_rank, z_score_rank


class TestSectorStrength:
    def test_basic_mean(self):
        returns = {"AAPL": 0.05, "MSFT": 0.03, "TSLA": -0.02}
        sectors = {"tech": ["AAPL", "MSFT"], "consumer": ["TSLA"]}
        result = sector_relative_strength(returns, sectors)
        assert result["tech"] == pytest.approx(0.04)
        assert result["consumer"] == pytest.approx(-0.02)

    def test_missing_symbol_skipped(self):
        returns = {"AAPL": 0.05}
        sectors = {"tech": ["AAPL", "GOOG"]}
        result = sector_relative_strength(returns, sectors)
        assert result["tech"] == pytest.approx(0.05)


class TestBreadth:
    def test_advance_decline_ratio(self):
        assert advance_decline_ratio(300, 200) == pytest.approx(1.5)

    def test_advance_decline_ratio_zero_declines(self):
        assert advance_decline_ratio(300, 0) is None

    def test_breadth_thrust_basic(self):
        advances = [250] * 10
        totals = [500] * 10
        result = breadth_thrust(advances, totals)
        assert result == pytest.approx(0.5)


class TestRelativeRank:
    _UNIVERSE = {"AAPL": 0.10, "MSFT": 0.05, "GOOG": 0.02, "TSLA": -0.03}

    def test_percentile_rank_top(self):
        pct = percentile_rank("AAPL", self._UNIVERSE)
        assert pct == pytest.approx(100.0)

    def test_percentile_rank_bottom(self):
        pct = percentile_rank("TSLA", self._UNIVERSE)
        assert pct == pytest.approx(0.0)

    def test_percentile_rank_missing(self):
        assert percentile_rank("AMZN", self._UNIVERSE) is None

    def test_z_score_rank(self):
        score = z_score_rank("AAPL", self._UNIVERSE)
        assert score is not None
        assert score > 0
