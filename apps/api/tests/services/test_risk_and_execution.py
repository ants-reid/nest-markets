"""Tests for RiskService, RiskProfileService, and ExecutionModeService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.db.models import ExecutionMode, RiskProfile
from app.services.execution_mode_service import (
    ExecutionModeService,
    MODE_PAPER,
    MODE_PENDING_APPROVAL,
)
from app.services.risk_profile_service import RiskDefaults, RiskProfileService
from app.services.risk_service import RiskInput, RiskService


# --------------------------------------------------------------------------- #
# Shared fixtures                                                              #
# --------------------------------------------------------------------------- #


@pytest.fixture
def mock_session() -> MagicMock:
    """Return a mock SQLAlchemy session."""
    return MagicMock(spec=Session)


@pytest.fixture
def default_profile() -> RiskProfile:
    """Return an in-memory RiskProfile built from MVP defaults."""
    d = RiskDefaults()
    return RiskProfile(
        id=uuid4(),
        name="test_profile",
        is_active="active",
        max_open_positions=d.max_open_positions,
        max_correlated_bucket_exposure=d.max_correlated_bucket_exposure,
        max_risk_per_trade_pct=d.max_risk_per_trade_pct,
        max_daily_drawdown_pct=d.max_daily_drawdown_pct,
        min_confidence=d.min_confidence,
        min_signal_score=d.min_signal_score,
        max_spread_bps_fx=d.max_spread_bps_fx,
        max_spread_bps_equity=d.max_spread_bps_equity,
        cooldown_after_3_losses_min=d.cooldown_after_3_losses_min,
    )


@pytest.fixture
def passing_risk_input(default_profile) -> RiskInput:
    """Return a RiskInput that passes every rule."""
    return RiskInput(
        signal_id=uuid4(),
        asset_id=uuid4(),
        asset_symbol="EURUSD",
        direction="long",
        confidence=0.75,
        signal_score=80.0,
        spread_bps=5.0,
        asset_type="fx",
        daily_drawdown_pct=0.5,
        open_positions_count=2,
        recent_losses_count=0,
        last_loss_at=None,
        kill_switch_active=False,
        risk_profile=default_profile,
    )


def _risk_service_with_mock_session(mock_session: MagicMock) -> RiskService:
    """Wire up RiskService with a session whose commit/refresh are no-ops."""
    service = RiskService(mock_session)
    # Simulate commit and refresh so _persist_decision doesn't raise.
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()

    def _refresh(obj):
        if obj.id is None:
            obj.id = uuid4()

    mock_session.refresh = MagicMock(side_effect=_refresh)
    return service


# --------------------------------------------------------------------------- #
# RiskProfileService                                                           #
# --------------------------------------------------------------------------- #


class TestRiskProfileService:
    """Tests for RiskProfileService."""

    def test_get_defaults_returns_mvp_values(self):
        """get_defaults() should return the hard-coded MVP thresholds."""
        defaults = RiskProfileService.get_defaults()
        assert defaults.min_confidence == 0.62
        assert defaults.min_signal_score == 68.0
        assert defaults.max_spread_bps_fx == 12.0
        assert defaults.max_spread_bps_equity == 25.0
        assert defaults.max_daily_drawdown_pct == 2.00
        assert defaults.cooldown_after_3_losses_min == 180.0

    def test_get_active_profile_returns_db_row(self, mock_session, default_profile):
        """get_active_profile() should return the queried profile."""
        mock_session.query.return_value.filter.return_value.first.return_value = default_profile
        service = RiskProfileService(mock_session)
        profile = service.get_active_profile()
        assert profile is default_profile

    def test_get_active_profile_raises_when_none(self, mock_session):
        """get_active_profile() should raise ValueError when no active profile."""
        mock_session.query.return_value.filter.return_value.first.return_value = None
        service = RiskProfileService(mock_session)
        with pytest.raises(ValueError, match="No active risk profile found"):
            service.get_active_profile()

    def test_get_active_profile_or_defaults_falls_back(self, mock_session):
        """get_active_profile_or_defaults() should not raise when DB is empty."""
        mock_session.query.return_value.filter.return_value.first.return_value = None
        service = RiskProfileService(mock_session)
        profile = service.get_active_profile_or_defaults()
        assert profile.name == "__defaults__"
        assert profile.min_confidence == RiskDefaults().min_confidence


# --------------------------------------------------------------------------- #
# RiskService — individual rule checks                                         #
# --------------------------------------------------------------------------- #


class TestRiskServiceRules:
    """Unit tests for each individual blocking rule."""

    def setup_method(self):
        """Create a detached service for rule-method testing."""
        self._session = MagicMock(spec=Session)
        self.service = RiskService(self._session)
        self.profile = RiskDefaults()

    # Convenience: build a fake RiskProfile from RiskDefaults
    @property
    def _profile(self) -> RiskProfile:
        d = RiskDefaults()
        return RiskProfile(
            id=uuid4(),
            name="p",
            is_active="active",
            max_open_positions=d.max_open_positions,
            max_correlated_bucket_exposure=d.max_correlated_bucket_exposure,
            max_risk_per_trade_pct=d.max_risk_per_trade_pct,
            max_daily_drawdown_pct=d.max_daily_drawdown_pct,
            min_confidence=d.min_confidence,
            min_signal_score=d.min_signal_score,
            max_spread_bps_fx=d.max_spread_bps_fx,
            max_spread_bps_equity=d.max_spread_bps_equity,
            cooldown_after_3_losses_min=d.cooldown_after_3_losses_min,
        )

    # ---- direction -------------------------------------------------------- #

    def test_direction_flat_blocks(self):
        """Flat direction must be blocked."""
        result = self.service._check_direction("flat")
        assert result is not None
        assert "flat" in result.lower()

    def test_direction_long_passes(self):
        """Long direction must not be blocked."""
        assert self.service._check_direction("long") is None

    def test_direction_short_passes(self):
        """Short direction must not be blocked."""
        assert self.service._check_direction("short") is None

    # ---- confidence ------------------------------------------------------- #

    def test_confidence_below_threshold_blocks(self):
        """Confidence below min_confidence must be blocked."""
        profile = self._profile
        profile.min_confidence = 0.62
        result = self.service._check_confidence(0.50, profile)
        assert result is not None
        assert "0.500" in result

    def test_confidence_at_threshold_passes(self):
        """Confidence exactly at threshold must pass."""
        profile = self._profile
        profile.min_confidence = 0.62
        assert self.service._check_confidence(0.62, profile) is None

    def test_confidence_above_threshold_passes(self):
        """Confidence above threshold must pass."""
        profile = self._profile
        assert self.service._check_confidence(0.90, profile) is None

    # ---- signal score ----------------------------------------------------- #

    def test_signal_score_below_threshold_blocks(self):
        """Signal score below min_signal_score must be blocked."""
        profile = self._profile
        profile.min_signal_score = 68.0
        result = self.service._check_signal_score(55.0, profile)
        assert result is not None
        assert "55.0" in result

    def test_signal_score_at_threshold_passes(self):
        """Signal score exactly at threshold must pass."""
        profile = self._profile
        profile.min_signal_score = 68.0
        assert self.service._check_signal_score(68.0, profile) is None

    def test_signal_score_above_threshold_passes(self):
        """Signal score above threshold must pass."""
        profile = self._profile
        assert self.service._check_signal_score(90.0, profile) is None

    # ---- spread ----------------------------------------------------------- #

    def test_spread_too_wide_fx_blocks(self):
        """FX spread above max_spread_bps_fx must be blocked."""
        profile = self._profile
        result = self.service._check_spread(15.0, "fx", profile)
        assert result is not None
        assert "15.0" in result
        assert "fx" in result.lower()

    def test_spread_at_fx_cap_passes(self):
        """FX spread exactly at cap must pass."""
        profile = self._profile
        assert self.service._check_spread(12.0, "fx", profile) is None

    def test_spread_too_wide_equity_blocks(self):
        """Equity spread above max_spread_bps_equity must be blocked."""
        profile = self._profile
        result = self.service._check_spread(30.0, "equity", profile)
        assert result is not None
        assert "equity" in result.lower()

    def test_spread_acceptable_equity_passes(self):
        """Equity spread within cap must pass."""
        profile = self._profile
        assert self.service._check_spread(20.0, "equity", profile) is None

    # ---- drawdown --------------------------------------------------------- #

    def test_drawdown_at_limit_blocks(self):
        """Drawdown at max_daily_drawdown_pct must be blocked."""
        profile = self._profile
        profile.max_daily_drawdown_pct = 2.00
        result = self.service._check_drawdown(2.00, profile)
        assert result is not None
        assert "2.00" in result

    def test_drawdown_exceeded_blocks(self):
        """Drawdown above limit must be blocked."""
        profile = self._profile
        result = self.service._check_drawdown(2.50, profile)
        assert result is not None

    def test_drawdown_below_limit_passes(self):
        """Drawdown below limit must pass."""
        profile = self._profile
        assert self.service._check_drawdown(1.0, profile) is None

    # ---- kill switch ------------------------------------------------------ #

    def test_kill_switch_active_blocks(self):
        """Active kill switch must block."""
        result = self.service._check_kill_switch(True)
        assert result is not None
        assert "kill switch" in result.lower()

    def test_kill_switch_inactive_passes(self):
        """Inactive kill switch must pass."""
        assert self.service._check_kill_switch(False) is None

    # ---- position limit --------------------------------------------------- #

    def test_position_limit_reached_blocks(self):
        """Reaching max_open_positions must be blocked."""
        profile = self._profile
        profile.max_open_positions = 6.0
        result = self.service._check_position_limit(6, profile)
        assert result is not None

    def test_position_limit_not_reached_passes(self):
        """Open positions below cap must pass."""
        profile = self._profile
        assert self.service._check_position_limit(3, profile) is None

    # ---- cooldown --------------------------------------------------------- #

    def test_cooldown_active_when_3_losses_recent(self):
        """Cooldown must trigger with 3 losses within cooldown window."""
        profile = self._profile
        profile.cooldown_after_3_losses_min = 180.0
        recent_loss = datetime.now(UTC) - timedelta(minutes=30)
        active, reason = self.service._check_cooldown(3, recent_loss, profile)
        assert active is True
        assert reason is not None
        assert "cooldown" in reason.lower()

    def test_cooldown_inactive_when_window_expired(self):
        """Cooldown must not trigger once the cooldown window has passed."""
        profile = self._profile
        profile.cooldown_after_3_losses_min = 180.0
        old_loss = datetime.now(UTC) - timedelta(minutes=200)
        active, reason = self.service._check_cooldown(3, old_loss, profile)
        assert active is False
        assert reason is None

    def test_cooldown_inactive_with_fewer_than_3_losses(self):
        """Cooldown must not trigger with fewer than 3 losses."""
        profile = self._profile
        recent_loss = datetime.now(UTC) - timedelta(minutes=10)
        active, reason = self.service._check_cooldown(2, recent_loss, profile)
        assert active is False
        assert reason is None

    def test_cooldown_inactive_when_no_loss_time(self):
        """Cooldown must not trigger when last_loss_at is None."""
        profile = self._profile
        active, reason = self.service._check_cooldown(5, None, profile)
        assert active is False

    def test_cooldown_handles_naive_datetime(self):
        """Cooldown must handle naive datetimes by treating them as UTC."""
        profile = self._profile
        profile.cooldown_after_3_losses_min = 180.0
        naive_loss = (datetime.now(UTC) - timedelta(minutes=30)).replace(tzinfo=None)
        active, reason = self.service._check_cooldown(3, naive_loss, profile)
        assert active is True


# --------------------------------------------------------------------------- #
# RiskService — full evaluate() path                                          #
# --------------------------------------------------------------------------- #


class TestRiskServiceEvaluate:
    """Integration-style tests for the full evaluate() call."""

    def test_evaluate_approves_passing_signal(self, mock_session, passing_risk_input):
        """evaluate() must return approved when all rules pass."""
        service = _risk_service_with_mock_session(mock_session)
        output = service.evaluate(passing_risk_input)
        assert output.approved is True
        assert output.decision == "approved"
        assert output.blocking_rule is None

    def test_evaluate_rejects_on_flat_direction(self, mock_session, default_profile):
        """evaluate() must reject a flat-direction signal."""
        service = _risk_service_with_mock_session(mock_session)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="AAPL",
            direction="flat",
            confidence=0.90,
            signal_score=85.0,
            spread_bps=5.0,
            asset_type="equity",
            daily_drawdown_pct=0.1,
            open_positions_count=0,
            recent_losses_count=0,
            last_loss_at=None,
            kill_switch_active=False,
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.approved is False
        assert output.blocking_rule == "direction_flat"

    def test_evaluate_rejects_on_low_confidence(self, mock_session, default_profile):
        """evaluate() must reject when confidence is below threshold."""
        service = _risk_service_with_mock_session(mock_session)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="AAPL",
            direction="long",
            confidence=0.50,         # Below 0.62
            signal_score=80.0,
            spread_bps=5.0,
            asset_type="equity",
            daily_drawdown_pct=0.0,
            open_positions_count=0,
            recent_losses_count=0,
            last_loss_at=None,
            kill_switch_active=False,
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.approved is False
        assert output.blocking_rule == "confidence_below_threshold"

    def test_evaluate_rejects_on_low_signal_score(self, mock_session, default_profile):
        """evaluate() must reject when signal score is below threshold."""
        service = _risk_service_with_mock_session(mock_session)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="AAPL",
            direction="long",
            confidence=0.80,
            signal_score=50.0,       # Below 68
            spread_bps=5.0,
            asset_type="equity",
            daily_drawdown_pct=0.0,
            open_positions_count=0,
            recent_losses_count=0,
            last_loss_at=None,
            kill_switch_active=False,
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.approved is False
        assert output.blocking_rule == "signal_score_below_threshold"

    def test_evaluate_rejects_on_wide_spread(self, mock_session, default_profile):
        """evaluate() must reject when spread exceeds asset-class cap."""
        service = _risk_service_with_mock_session(mock_session)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="EURUSD",
            direction="long",
            confidence=0.80,
            signal_score=80.0,
            spread_bps=20.0,        # Exceeds fx cap of 12
            asset_type="fx",
            daily_drawdown_pct=0.0,
            open_positions_count=0,
            recent_losses_count=0,
            last_loss_at=None,
            kill_switch_active=False,
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.approved is False
        assert output.blocking_rule == "spread_too_wide"

    def test_evaluate_rejects_on_drawdown_exceeded(self, mock_session, default_profile):
        """evaluate() must reject when daily drawdown limit is hit."""
        service = _risk_service_with_mock_session(mock_session)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="AAPL",
            direction="long",
            confidence=0.80,
            signal_score=80.0,
            spread_bps=5.0,
            asset_type="equity",
            daily_drawdown_pct=2.50,  # Exceeds 2.00 limit
            open_positions_count=0,
            recent_losses_count=0,
            last_loss_at=None,
            kill_switch_active=False,
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.approved is False
        assert output.blocking_rule == "drawdown_exceeded"

    def test_evaluate_rejects_on_cooldown(self, mock_session, default_profile):
        """evaluate() must reject when cooldown is active."""
        service = _risk_service_with_mock_session(mock_session)
        recent_loss = datetime.now(UTC) - timedelta(minutes=30)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="AAPL",
            direction="long",
            confidence=0.80,
            signal_score=80.0,
            spread_bps=5.0,
            asset_type="equity",
            daily_drawdown_pct=0.0,
            open_positions_count=0,
            recent_losses_count=3,   # Triggers cooldown
            last_loss_at=recent_loss,
            kill_switch_active=False,
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.approved is False
        assert output.blocking_rule == "cooldown_active"
        assert output.cooldown_active is True

    def test_evaluate_rejects_on_kill_switch(self, mock_session, default_profile):
        """evaluate() must reject when kill switch is active."""
        service = _risk_service_with_mock_session(mock_session)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="AAPL",
            direction="long",
            confidence=0.80,
            signal_score=80.0,
            spread_bps=5.0,
            asset_type="equity",
            daily_drawdown_pct=0.0,
            open_positions_count=0,
            recent_losses_count=0,
            last_loss_at=None,
            kill_switch_active=True,  # Kill switch on
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.approved is False
        assert output.blocking_rule == "kill_switch_active"
        assert output.kill_switch_active is True

    def test_evaluate_persists_risk_decision(self, mock_session, passing_risk_input):
        """evaluate() must call session.add and session.commit once."""
        service = _risk_service_with_mock_session(mock_session)
        service.evaluate(passing_risk_input)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_evaluate_first_blocking_rule_wins(self, mock_session, default_profile):
        """When multiple rules fail, the first one in priority order must block."""
        service = _risk_service_with_mock_session(mock_session)
        risk_input = RiskInput(
            signal_id=uuid4(),
            asset_id=uuid4(),
            asset_symbol="EURUSD",
            direction="flat",        # Rule 1 — should block here
            confidence=0.10,         # Would also fail rule 2
            signal_score=10.0,       # Would also fail rule 3
            spread_bps=999.0,        # Would also fail rule 4
            asset_type="fx",
            daily_drawdown_pct=99.0, # Would also fail rule 5
            open_positions_count=99,
            recent_losses_count=10,
            last_loss_at=datetime.now(UTC),
            kill_switch_active=True,
            risk_profile=default_profile,
        )
        output = service.evaluate(risk_input)
        assert output.blocking_rule == "direction_flat"


# --------------------------------------------------------------------------- #
# ExecutionModeService                                                         #
# --------------------------------------------------------------------------- #


class TestExecutionModeService:
    """Tests for ExecutionModeService routing logic."""

    def _make_mode(self, name: str, requires_approval: str = "inactive") -> ExecutionMode:
        """Build an in-memory ExecutionMode record."""
        return ExecutionMode(
            id=uuid4(),
            name=name,
            is_active="active",
            requires_approval=requires_approval,
            allows_live_orders="inactive",
        )

    def test_get_route_returns_paper_mode(self, mock_session):
        """get_route() must return paper routing for paper mode."""
        mode = self._make_mode(MODE_PAPER)
        mock_session.query.return_value.filter.return_value.first.return_value = mode
        service = ExecutionModeService(mock_session)
        route = service.get_route()
        assert route.mode == MODE_PAPER
        assert route.requires_approval is False
        assert route.allows_live_orders is False

    def test_get_route_returns_pending_approval_mode(self, mock_session):
        """get_route() must set requires_approval=True for pending_approval mode."""
        mode = self._make_mode(MODE_PENDING_APPROVAL, requires_approval="active")
        mock_session.query.return_value.filter.return_value.first.return_value = mode
        service = ExecutionModeService(mock_session)
        route = service.get_route()
        assert route.mode == MODE_PENDING_APPROVAL
        assert route.requires_approval is True
        assert route.allows_live_orders is False

    def test_get_route_returns_auto_mode(self, mock_session):
        """get_route() must return auto routing for auto mode."""
        mode = self._make_mode("auto")
        mock_session.query.return_value.filter.return_value.first.return_value = mode
        service = ExecutionModeService(mock_session)
        route = service.get_route()
        assert route.mode == "auto"
        assert route.allows_live_orders is False

    def test_live_mode_downgraded_to_paper(self, mock_session):
        """get_route() must silently downgrade 'live' mode to paper in MVP."""
        mode = self._make_mode("live", requires_approval="inactive")
        mock_session.query.return_value.filter.return_value.first.return_value = mode
        service = ExecutionModeService(mock_session)
        route = service.get_route()
        assert route.mode == MODE_PAPER
        assert route.allows_live_orders is False

    def test_get_route_raises_when_no_active_mode(self, mock_session):
        """get_route() must raise ValueError when no active mode exists."""
        mock_session.query.return_value.filter.return_value.first.return_value = None
        service = ExecutionModeService(mock_session)
        with pytest.raises(ValueError, match="No active execution mode found"):
            service.get_route()

    def test_is_live_enabled_always_false(self, mock_session):
        """is_live_enabled() must always return False in MVP."""
        service = ExecutionModeService(mock_session)
        assert service.is_live_enabled() is False

    def test_execution_mode_id_propagated(self, mock_session):
        """get_route() must carry the ExecutionMode ID into the route."""
        mode = self._make_mode(MODE_PAPER)
        mock_session.query.return_value.filter.return_value.first.return_value = mode
        service = ExecutionModeService(mock_session)
        route = service.get_route()
        assert route.execution_mode_id == mode.id

    def test_pending_approval_without_flag_does_not_require_approval(self, mock_session):
        """pending_approval mode with requires_approval='inactive' must not require approval."""
        mode = self._make_mode(MODE_PENDING_APPROVAL, requires_approval="inactive")
        mock_session.query.return_value.filter.return_value.first.return_value = mode
        service = ExecutionModeService(mock_session)
        route = service.get_route()
        assert route.requires_approval is False
