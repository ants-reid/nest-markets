"""Persistence mappers for signals and deterministic risk decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import CatalystType, HorizonLabel, RegimeType, SetupType, SignalStatus, TradeDirection
from app.db.models.asset import Asset
from app.db.models.feature_snapshot import FeatureSnapshot
from app.db.models.risk_decision import RiskDecision as RiskDecisionModel
from app.db.models.signal import Signal as SignalModel
from app.db.models.mixins import utc_now
from app.services.feature_service import FeatureSnapshotPayload
from app.services.risk_service import RiskDecision
from app.services.signal_service import SignalOutput


class PersistenceSignalService:
    """Persist signal and risk decision outputs into ORM models."""

    def __init__(self, session: Session) -> None:
        """Initialize service with an explicit SQLAlchemy session."""
        self._session = session

    def persist_signal(
        self,
        signal_output: SignalOutput,
        *,
        scan_ts: datetime | None = None,
        signal_status: SignalStatus = SignalStatus.CANDIDATE,
        provider_name: str | None = None,
        raw_llm_json: dict[str, Any] | None = None,
        feature_snapshot_id: UUID | None = None,
        prompt_version_id: UUID | None = None,
        model_version_id: UUID | None = None,
        signal_id: UUID | None = None,
    ) -> SignalModel:
        """Create or update a persisted signal row from a typed signal output."""
        asset = self._get_asset_by_symbol(signal_output.asset)
        signal = self._get_signal(signal_id)

        if signal is None:
            signal = SignalModel(
                id=signal_id,
                asset_id=asset.id,
                scan_ts=scan_ts or utc_now(),
                timeframe=signal_output.timeframe,
                signal_status=signal_status,
                direction=self._map_direction(signal_output.direction),
                setup_type=self._map_setup_type(signal_output.setup_type),
                regime=self._map_regime(signal_output.regime),
                entry_min=signal_output.entry_zone[0],
                entry_max=signal_output.entry_zone[1],
                stop_price=signal_output.stop_price,
                target_price=signal_output.target_price,
                confidence=signal_output.confidence,
                horizon_label=self._map_horizon_label(signal_output.horizon_label),
                catalyst_type=self._map_catalyst_type(signal_output.catalyst_type),
                catalyst_score=signal_output.catalyst_score,
                catalyst_summary=signal_output.catalyst_summary,
                thesis=signal_output.thesis,
                invalidators_json=list(signal_output.invalidators),
                signal_score=signal_output.signal_score,
                raw_llm_json=raw_llm_json,
                provider_name=provider_name,
                feature_snapshot_id=feature_snapshot_id,
                prompt_version_id=prompt_version_id,
                model_version_id=model_version_id,
            )
            self._session.add(signal)
        else:
            signal.asset_id = asset.id
            signal.scan_ts = scan_ts or signal.scan_ts
            signal.timeframe = signal_output.timeframe
            signal.signal_status = signal_status
            signal.direction = self._map_direction(signal_output.direction)
            signal.setup_type = self._map_setup_type(signal_output.setup_type)
            signal.regime = self._map_regime(signal_output.regime)
            signal.entry_min = signal_output.entry_zone[0]
            signal.entry_max = signal_output.entry_zone[1]
            signal.stop_price = signal_output.stop_price
            signal.target_price = signal_output.target_price
            signal.confidence = signal_output.confidence
            signal.horizon_label = self._map_horizon_label(signal_output.horizon_label)
            signal.catalyst_type = self._map_catalyst_type(signal_output.catalyst_type)
            signal.catalyst_score = signal_output.catalyst_score
            signal.catalyst_summary = signal_output.catalyst_summary
            signal.thesis = signal_output.thesis
            signal.invalidators_json = list(signal_output.invalidators)
            signal.signal_score = signal_output.signal_score
            signal.raw_llm_json = raw_llm_json
            signal.provider_name = provider_name
            signal.feature_snapshot_id = feature_snapshot_id
            signal.prompt_version_id = prompt_version_id
            signal.model_version_id = model_version_id

        self._session.flush()
        self._session.refresh(signal)
        return signal

    def persist_risk_decision(self, signal_id: UUID, decision: RiskDecision) -> RiskDecisionModel:
        """Create or update a persisted deterministic risk decision row."""
        row = self._get_risk_decision(signal_id)

        if row is None:
            row = RiskDecisionModel(signal_id=signal_id, approved=decision.approved)
            self._session.add(row)

        row.approved = decision.approved
        row.blocked_reasons_json = list(decision.blocked_reasons)
        row.notional_allowed = decision.allowed_risk_amount
        row.spread_ok = False
        row.session_ok = True
        row.drawdown_ok = False
        row.cooldown_ok = False
        row.kill_switch_active = False
        row.decision_json = {
            "approved": decision.approved,
            "blocked_reasons": list(decision.blocked_reasons),
            "allowed_risk_amount": decision.allowed_risk_amount,
            "selected_execution_mode": decision.selected_execution_mode,
        }

        self._session.flush()
        self._session.refresh(row)
        return row

    def persist_feature_snapshot(
        self,
        payload: FeatureSnapshotPayload,
        *,
        asset_id: UUID,
        timeframe: str,
        scan_ts: datetime | None = None,
        signal_id: UUID | None = None,
    ) -> FeatureSnapshot:
        """Persist a FeatureSnapshotPayload into the feature_snapshots table."""
        ts = scan_ts or utc_now()
        row = FeatureSnapshot(
            asset_id=asset_id,
            signal_id=signal_id,
            scan_ts=ts,
            timeframe=timeframe,
            trend_score=payload.trend_score,
            momentum_score=payload.momentum_score,
            volatility_score=payload.volatility_score,
            liquidity_score=payload.liquidity_score,
            regime=self._map_feature_regime(payload.regime_preclassification),
            atr=payload.atr,
            rsi=payload.rsi,
            ema_fast=payload.ema_fast,
            ema_slow=payload.ema_slow,
            adx=payload.adx,
            market_quality_flag="good" if payload.market_quality_flag else "poor",
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return row

    def _get_asset_by_symbol(self, symbol: str) -> Asset:
        """Return the persisted asset row for a symbol or raise."""
        statement = select(Asset).where(Asset.symbol == symbol)
        asset = self._session.execute(statement).scalar_one_or_none()
        if asset is None:
            raise ValueError(f"Asset '{symbol}' must exist before persisting a signal")
        return asset

    def _get_signal(self, signal_id: UUID | None) -> SignalModel | None:
        """Return an existing signal row when a signal id is provided."""
        if signal_id is None:
            return None
        return self._session.get(SignalModel, signal_id)

    def _get_risk_decision(self, signal_id: UUID) -> RiskDecisionModel | None:
        """Return an existing risk decision row for a signal if present."""
        statement = select(RiskDecisionModel).where(RiskDecisionModel.signal_id == signal_id)
        return self._session.execute(statement).scalar_one_or_none()

    def _map_direction(self, value: str) -> TradeDirection:
        """Map domain direction string to ORM enum."""
        return TradeDirection(value)

    def _map_setup_type(self, value: str) -> SetupType:
        """Map domain setup type string to ORM enum."""
        return SetupType(value)

    def _map_regime(self, value: str) -> RegimeType:
        """Map domain regime string to ORM enum."""
        return RegimeType(value)

    def _map_horizon_label(self, value: str) -> HorizonLabel:
        """Map domain horizon label string to ORM enum."""
        return HorizonLabel(value)

    def _map_catalyst_type(self, value: str) -> CatalystType:
        """Map domain catalyst type string to ORM enum."""
        return CatalystType(value)

    @staticmethod
    def _map_feature_regime(value: str) -> RegimeType:
        """Map classify_regime output strings to RegimeType ORM enum."""
        _table: dict[str, RegimeType] = {
            "trending_up": RegimeType.TREND,
            "trending_down": RegimeType.TREND,
            "trend": RegimeType.TREND,
            "ranging": RegimeType.RANGE,
            "range": RegimeType.RANGE,
            "mean_reversion": RegimeType.RANGE,
            "high_vol": RegimeType.HIGH_VOLATILITY,
            "high_volatility": RegimeType.HIGH_VOLATILITY,
            "low_vol": RegimeType.LOW_VOLATILITY,
            "low_volatility": RegimeType.LOW_VOLATILITY,
            "breakout": RegimeType.BREAKOUT,
            "risk_on": RegimeType.RISK_ON,
            "risk_off": RegimeType.RISK_OFF,
        }
        return _table.get(value.lower(), RegimeType.RANGE)
