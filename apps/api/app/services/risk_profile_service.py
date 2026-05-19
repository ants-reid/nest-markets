"""Deterministic risk profile thresholds for MVP evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import RiskProfile as RiskProfileModel


@dataclass(frozen=True)
class RiskDefaults:
    """Hard-coded MVP risk thresholds."""

    min_confidence: float = 0.62
    min_signal_score: float = 68.0
    max_spread_bps_fx: float = 12.0
    max_spread_bps_equity: float = 25.0
    max_daily_drawdown_pct: float = 2.0
    cooldown_after_3_losses_min: float = 180.0
    max_open_positions: float = 6.0
    max_correlated_bucket_exposure: float = 2.0
    max_risk_per_trade_pct: float = 0.50


# Legacy dataclass kept for backward compat with RiskEvaluator
@dataclass(frozen=True)
class RiskProfile:
    """Legacy risk profile dataclass (used by RiskEvaluator in route handlers)."""

    min_confidence: float = 0.62
    min_signal_score: float = 68.0
    max_spread_bps: float = 25.0
    max_daily_drawdown_pct: float = 2.0
    cooldown_after_losses_min: int = 180
    max_correlated_exposure: int = 2
    capital_cap: float = 100000.0
    max_risk_per_trade_pct: float = 0.50


class RiskProfileService:
    """Provides MVP risk profiles from DB or defaults."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @staticmethod
    def get_defaults() -> RiskDefaults:
        """Return the hard-coded MVP default thresholds."""
        return RiskDefaults()

    def get_default_profile(self) -> RiskProfile:
        """Return the legacy default risk profile (for backward compat)."""
        return RiskProfile()

    def get_active_profile(self) -> RiskProfileModel:
        """Return the active risk profile from DB.

        Raises:
            ValueError: If no active profile exists.
            RuntimeError: If no session provided.
        """
        if self._session is None:
            raise RuntimeError("Session required for get_active_profile")
        profile: RiskProfileModel | None = (
            self._session.query(RiskProfileModel)
            .filter(RiskProfileModel.is_active == "active")
            .first()
        )
        if profile is None:
            raise ValueError("No active risk profile found")
        return profile

    def get_active_profile_or_defaults(self) -> RiskProfileModel:
        """Return active DB profile or a defaults-based profile if none exists."""
        if self._session is not None:
            try:
                return self.get_active_profile()
            except ValueError:
                pass
        d = RiskDefaults()
        return RiskProfileModel(
            name="__defaults__",
            is_active="inactive",
            min_confidence=d.min_confidence,
            min_signal_score=d.min_signal_score,
            max_spread_bps_fx=d.max_spread_bps_fx,
            max_spread_bps_equity=d.max_spread_bps_equity,
            max_daily_drawdown_pct=d.max_daily_drawdown_pct,
            cooldown_after_3_losses_min=d.cooldown_after_3_losses_min,
            max_open_positions=d.max_open_positions,
            max_correlated_bucket_exposure=d.max_correlated_bucket_exposure,
            max_risk_per_trade_pct=d.max_risk_per_trade_pct,
        )
