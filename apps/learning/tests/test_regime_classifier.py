"""Phase 7 — regime classifier tests."""

from __future__ import annotations

import pytest

from apps.learning.services.regime.regime_classifier import RegimeClassifier, RegimeInput
from apps.learning.services.regime.regime_snapshot_service import RegimeSnapshotService
from apps.learning.services.regime.regime_validation_service import RegimeValidationService
from datetime import date


@pytest.fixture
def classifier():
    return RegimeClassifier()


class TestRegimeClassifier:
    def test_high_vol_on_elevated_vix(self, classifier):
        inputs = RegimeInput(vix=35, spy_roc_21=0.01, advance_decline_ratio=1.0, yield_curve_slope=0.5)
        result = classifier.classify(inputs)
        assert result.regime == "high_vol"

    def test_risk_on_conditions(self, classifier):
        inputs = RegimeInput(vix=12, spy_roc_21=0.02, advance_decline_ratio=1.3, yield_curve_slope=1.0)
        result = classifier.classify(inputs)
        assert result.regime == "risk_on"

    def test_low_vol_mixed_breadth(self, classifier):
        inputs = RegimeInput(vix=12, spy_roc_21=-0.01, advance_decline_ratio=0.9, yield_curve_slope=0.5)
        result = classifier.classify(inputs)
        assert result.regime == "low_vol"

    def test_trend_on_strong_momentum(self, classifier):
        inputs = RegimeInput(vix=20, spy_roc_21=0.05, advance_decline_ratio=1.2, yield_curve_slope=0.8)
        result = classifier.classify(inputs)
        assert result.regime == "trend"

    def test_chop_on_flat_momentum(self, classifier):
        inputs = RegimeInput(vix=18, spy_roc_21=0.002, advance_decline_ratio=1.0, yield_curve_slope=0.5)
        result = classifier.classify(inputs)
        assert result.regime == "chop"

    def test_confidence_in_range(self, classifier):
        inputs = RegimeInput(vix=25, spy_roc_21=0.0, advance_decline_ratio=0.8, yield_curve_slope=-0.1)
        result = classifier.classify(inputs)
        assert 0.0 <= result.confidence <= 1.0


class TestRegimeSnapshotService:
    def test_capture_returns_snapshot(self):
        svc = RegimeSnapshotService()
        inputs = RegimeInput(vix=35, spy_roc_21=0.0, advance_decline_ratio=0.8, yield_curve_slope=-0.2)
        snap = svc.capture(inputs, snapshot_date=date(2024, 1, 15))
        assert snap.snapshot_date == date(2024, 1, 15)
        assert snap.regime in {"risk_on", "risk_off", "high_vol", "low_vol", "chop", "trend"}

    def test_latest_returns_most_recent(self):
        svc = RegimeSnapshotService()
        inputs = RegimeInput(vix=20, spy_roc_21=0.01, advance_decline_ratio=1.1, yield_curve_slope=0.5)
        svc.capture(inputs, snapshot_date=date(2024, 1, 1))
        svc.capture(inputs, snapshot_date=date(2024, 1, 2))
        assert svc.latest().snapshot_date == date(2024, 1, 2)

    def test_history_grows(self):
        svc = RegimeSnapshotService()
        inputs = RegimeInput(vix=18, spy_roc_21=0.02, advance_decline_ratio=1.0, yield_curve_slope=0.5)
        svc.capture(inputs)
        svc.capture(inputs)
        assert len(svc.history()) == 2


class TestRegimeValidationService:
    def test_valid_regime_passes(self):
        svc = RegimeValidationService()
        errors = svc.validate_output("risk_on", 0.8)
        assert errors == []

    def test_invalid_regime_fails(self):
        svc = RegimeValidationService()
        errors = svc.validate_output("unknown", 0.5)
        assert len(errors) == 1

    def test_confidence_out_of_range(self):
        svc = RegimeValidationService()
        errors = svc.validate_output("chop", 1.5)
        assert len(errors) == 1

    def test_implausible_transition_flagged(self):
        svc = RegimeValidationService()
        errors = svc.validate_transition("low_vol", "high_vol")
        assert len(errors) == 1

    def test_normal_transition_passes(self):
        svc = RegimeValidationService()
        errors = svc.validate_transition("chop", "trend")
        assert errors == []
