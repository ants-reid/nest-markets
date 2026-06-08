"""Deterministic risk gating service for MVP signal approval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import RiskDecision as RiskDecisionModel
from app.db.models import RiskProfile as RiskProfileModel
from app.services.execution_mode_service import ExecutionModeService
from app.services.risk_profile_service import RiskProfile

ExecutionMode = Literal["paper", "confirm_live", "auto_live"]

_MAX_OPEN_POSITIONS_MVP = 6


# --------------------------------------------------------------------------- #
# Legacy API (used by existing route handlers)                                #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RiskContext:
    """Current risk/account context used to evaluate a candidate signal."""

    spread_bps: float
    daily_drawdown_pct: float
    consecutive_losses: int
    minutes_since_last_loss: int | None
    correlated_exposure_count: int
    market_quality_flag: bool
    account_equity: float
    requested_execution_mode: ExecutionMode
    session_allowed: bool = True
    kill_switch_active: bool = False
    open_positions_count: int = 0


@dataclass(frozen=True)
class RiskDecision:
    """Typed deterministic risk decision result (legacy)."""

    approved: bool
    blocked_reasons: list[str]
    allowed_risk_amount: float
    selected_execution_mode: Literal["paper", "confirm_live", "auto_live", "blocked"]


class RiskEvaluator:
    """Legacy risk evaluator (used by existing route handlers)."""

    def __init__(self, profile: RiskProfile, execution_mode_service: ExecutionModeService) -> None:
        self._profile = profile
        self._execution_mode_service = execution_mode_service

    def evaluate(self, signal, context: RiskContext) -> RiskDecision:
        blocked_reasons = self._collect_blocked_reasons(signal, context)
        approved = len(blocked_reasons) == 0
        allowed_risk_amount = self._allowed_risk_amount(context.account_equity) if approved else 0.0
        mode_decision = self._execution_mode_service.route(
            approved=approved,
            requested_mode=context.requested_execution_mode,
        )
        return RiskDecision(
            approved=approved,
            blocked_reasons=blocked_reasons,
            allowed_risk_amount=allowed_risk_amount,
            selected_execution_mode=mode_decision.selected_execution_mode,
        )

    def _collect_blocked_reasons(self, signal, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        if not context.session_allowed:
            reasons.append("session_not_allowed")
        if context.kill_switch_active:
            reasons.append("kill_switch_active")
        if context.open_positions_count >= _MAX_OPEN_POSITIONS_MVP:
            reasons.append("max_open_positions_exceeded")
        if not signal.should_trade or signal.direction == "flat":
            reasons.append("signal_not_actionable")
        if signal.confidence < self._profile.min_confidence:
            reasons.append("confidence_below_threshold")
        if signal.signal_score < self._profile.min_signal_score:
            reasons.append("signal_score_below_threshold")
        if context.spread_bps > self._profile.max_spread_bps:
            reasons.append("spread_above_cap")
        if context.daily_drawdown_pct >= self._profile.max_daily_drawdown_pct:
            reasons.append("daily_drawdown_exceeded")
        if self._is_cooldown_active(context):
            reasons.append("cooldown_active")
        if context.correlated_exposure_count >= self._profile.max_correlated_exposure:
            reasons.append("correlated_exposure_exceeded")
        if not context.market_quality_flag:
            reasons.append("market_quality_bad")
        if self._allowed_risk_amount(context.account_equity) <= 0.0:
            reasons.append("capital_or_risk_limit_block")
        return reasons

    def _is_cooldown_active(self, context: RiskContext) -> bool:
        if context.consecutive_losses < 3:
            return False
        if context.minutes_since_last_loss is None:
            return True
        return context.minutes_since_last_loss < self._profile.cooldown_after_losses_min

    def _allowed_risk_amount(self, account_equity: float) -> float:
        capped_equity = min(max(account_equity, 0.0), self._profile.capital_cap)
        return capped_equity * (self._profile.max_risk_per_trade_pct / 100.0)


# --------------------------------------------------------------------------- #
# New session-based API (used by tests and new route handlers)                #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RiskInput:
    """Input for session-based risk evaluation."""

    signal_id: UUID
    asset_id: UUID
    asset_symbol: str
    direction: str
    confidence: float
    signal_score: float
    spread_bps: float
    asset_type: str
    daily_drawdown_pct: float
    open_positions_count: int
    recent_losses_count: int
    last_loss_at: datetime | None
    kill_switch_active: bool
    risk_profile: RiskProfileModel


@dataclass
class RiskOutput:
    """Output of session-based risk evaluation."""

    approved: bool
    decision: str
    blocking_rule: str | None = None
    cooldown_active: bool = False
    kill_switch_active: bool = False


class RiskService:
    """Session-based deterministic risk gating service."""

    def __init__(
        self,
        session: Session | None = None,
        *,
        profile: RiskProfile | None = None,
        execution_mode_service: ExecutionModeService | None = None,
    ) -> None:
        self._session = session
        self._legacy_evaluator: RiskEvaluator | None = None

        if profile is not None or execution_mode_service is not None:
            if profile is None or execution_mode_service is None:
                raise TypeError(
                    "RiskService legacy mode requires both 'profile' and 'execution_mode_service'."
                )
            self._legacy_evaluator = RiskEvaluator(profile, execution_mode_service)

        if self._session is None and self._legacy_evaluator is None:
            raise TypeError(
                "RiskService requires either 'session' for persistence mode "
                "or both 'profile' and 'execution_mode_service' for legacy mode."
            )

    def evaluate(self, *args, **kwargs) -> RiskDecision | RiskOutput:
        """Evaluate risk in legacy or session mode based on constructor and args."""
        if self._legacy_evaluator is not None:
            signal = kwargs.get("signal") if "signal" in kwargs else (args[0] if len(args) > 0 else None)
            context = kwargs.get("context") if "context" in kwargs else (args[1] if len(args) > 1 else None)
            if signal is None or context is None:
                raise TypeError("Legacy evaluate requires 'signal' and 'context'.")
            return self._legacy_evaluator.evaluate(signal=signal, context=context)

        risk_input = kwargs.get("risk_input") if "risk_input" in kwargs else (args[0] if len(args) > 0 else None)
        if not isinstance(risk_input, RiskInput):
            raise TypeError("Session evaluate requires a RiskInput instance.")
        return self._evaluate_session(risk_input)

    def _evaluate_session(self, risk_input: RiskInput) -> RiskOutput:
        """Evaluate risk input against profile thresholds and persist decision."""
        if self._session is None:
            raise RuntimeError("Session mode is not available without a SQLAlchemy session.")
        profile = risk_input.risk_profile
        blocking_rule: str | None = None
        cooldown_active = False
        kill_switch = False

        # Evaluate rules in priority order — first failure wins
        check = self._check_direction(risk_input.direction)
        if check and blocking_rule is None:
            blocking_rule = "direction_flat"

        if blocking_rule is None:
            check = self._check_confidence(risk_input.confidence, profile)
            if check:
                blocking_rule = "confidence_below_threshold"

        if blocking_rule is None:
            check = self._check_signal_score(risk_input.signal_score, profile)
            if check:
                blocking_rule = "signal_score_below_threshold"

        if blocking_rule is None:
            check = self._check_spread(risk_input.spread_bps, risk_input.asset_type, profile)
            if check:
                blocking_rule = "spread_too_wide"

        if blocking_rule is None:
            check = self._check_drawdown(risk_input.daily_drawdown_pct, profile)
            if check:
                blocking_rule = "drawdown_exceeded"

        if blocking_rule is None:
            cooldown_on, _ = self._check_cooldown(
                risk_input.recent_losses_count, risk_input.last_loss_at, profile
            )
            if cooldown_on:
                cooldown_active = True
                blocking_rule = "cooldown_active"

        if blocking_rule is None:
            check = self._check_kill_switch(risk_input.kill_switch_active)
            if check:
                kill_switch = True
                blocking_rule = "kill_switch_active"

        if blocking_rule is None:
            check = self._check_position_limit(risk_input.open_positions_count, profile)
            if check:
                blocking_rule = "position_limit_exceeded"

        approved = blocking_rule is None
        decision_str = "approved" if approved else "rejected"

        # Persist
        db_decision = RiskDecisionModel(
            signal_id=risk_input.signal_id,
            approved=decision_str,
            blocking_rule=blocking_rule,
            kill_switch_active=risk_input.kill_switch_active,
            timestamp=datetime.now(UTC),
        )
        self._session.add(db_decision)
        self._session.commit()
        self._session.refresh(db_decision)

        return RiskOutput(
            approved=approved,
            decision=decision_str,
            blocking_rule=blocking_rule,
            cooldown_active=cooldown_active,
            kill_switch_active=kill_switch,
        )

    # ------------------------------------------------------------------ #
    # Individual rule checks                                               #
    # ------------------------------------------------------------------ #

    def _check_direction(self, direction: str) -> str | None:
        if direction == "flat":
            return "direction is flat"
        return None

    def _check_confidence(self, confidence: float, profile: RiskProfileModel) -> str | None:
        threshold = float(profile.min_confidence or 0.0)
        if confidence < threshold:
            return f"confidence {confidence:.3f} below threshold {threshold:.3f}"
        return None

    def _check_signal_score(self, score: float, profile: RiskProfileModel) -> str | None:
        threshold = float(profile.min_signal_score or 0.0)
        if score < threshold:
            return f"signal_score {score} below threshold {threshold}"
        return None

    def _check_spread(
        self, spread_bps: float, asset_type: str, profile: RiskProfileModel
    ) -> str | None:
        if asset_type == "fx":
            cap = float(profile.max_spread_bps_fx or 999.0)
        else:
            cap = float(profile.max_spread_bps_equity or 999.0)
        if spread_bps > cap:
            return f"spread {spread_bps} bps exceeds {asset_type} cap {cap}"
        return None

    def _check_drawdown(self, drawdown_pct: float, profile: RiskProfileModel) -> str | None:
        limit = float(profile.max_daily_drawdown_pct or 999.0)
        if drawdown_pct >= limit:
            return f"drawdown {drawdown_pct:.2f}% at or above limit {limit:.2f}%"
        return None

    def _check_kill_switch(self, active: bool) -> str | None:
        if active:
            return "kill switch is active"
        return None

    def _check_position_limit(
        self, open_positions_count: int, profile: RiskProfileModel
    ) -> str | None:
        limit = float(profile.max_open_positions or 999.0)
        if open_positions_count >= limit:
            return f"open positions {open_positions_count} at or above limit {limit}"
        return None

    def _check_cooldown(
        self,
        recent_losses_count: int,
        last_loss_at: datetime | None,
        profile: RiskProfileModel,
    ) -> tuple[bool, str | None]:
        if recent_losses_count < 3 or last_loss_at is None:
            return False, None
        cooldown_min = float(profile.cooldown_after_3_losses_min or 0.0)
        now = datetime.now(UTC)
        # Normalise naive datetimes to UTC
        if last_loss_at.tzinfo is None:
            last_loss_at = last_loss_at.replace(tzinfo=UTC)
        elapsed_min = (now - last_loss_at).total_seconds() / 60.0
        if elapsed_min < cooldown_min:
            return True, f"cooldown active: {elapsed_min:.1f} min elapsed of {cooldown_min} min"
        return False, None
