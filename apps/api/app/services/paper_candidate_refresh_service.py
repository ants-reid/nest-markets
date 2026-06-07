"""Paper candidate refresh service for supervised paper-mode testing.

This service only creates/refreshes CANDIDATE signals. It never submits orders,
never touches broker routes, and never mutates live trading controls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import AssetClass, CatalystType, HorizonLabel, RegimeType, SetupType, SignalStatus, TradeDirection
from app.db.models.asset import Asset
from app.db.models.signal import Signal
from app.services.visual_seed import provider_filter

_QUEUE_RECENCY_HOURS = 8
_QUEUE_MIN_SIGNAL_SCORE = 50.0
_REFRESH_PROVIDER = "paper_normal_refresh"
_DEFAULT_SIGNAL_SCORE = 97.0
_DEFAULT_CONFIDENCE = 0.93
_DEFAULT_TIMEFRAME = "1h"


@dataclass(frozen=True)
class CandidateRefreshItem:
    symbol: str
    action: str
    reason: str
    signal_id: str | None = None


class PaperCandidateRefreshService:
    """Create fresh paper-only candidates for allowlisted symbols.

    Behavior:
    - Creates one candidate per symbol when no recent eligible candidate exists.
    - Skips symbols with recent eligible candidates (prevents duplicate spam).
    - Skips symbols missing from the assets table.
    """

    def __init__(
        self,
        session: Session,
        *,
        provider_name: str = _REFRESH_PROVIDER,
        recency_hours: int = _QUEUE_RECENCY_HOURS,
    ) -> None:
        self._session = session
        self._provider_name = provider_name
        self._recency_hours = recency_hours

    def refresh(
        self,
        *,
        symbols: list[str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        now_utc = datetime.now(UTC)
        cutoff = now_utc - timedelta(hours=self._recency_hours)
        normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]

        if not normalized_symbols:
            return {
                "created_count": 0,
                "skipped_count": 0,
                "candidates": [],
            }

        assets = self._load_assets_by_symbol(normalized_symbols)

        created_count = 0
        skipped_count = 0
        items: list[CandidateRefreshItem] = []

        for symbol in normalized_symbols:
            asset = assets.get(symbol)
            if asset is None:
                skipped_count += 1
                items.append(CandidateRefreshItem(symbol=symbol, action="skipped", reason="asset_not_found"))
                continue

            if self._has_recent_eligible_candidate(asset_id=asset.id, cutoff=cutoff):
                skipped_count += 1
                items.append(
                    CandidateRefreshItem(
                        symbol=symbol,
                        action="skipped",
                        reason="recent_eligible_candidate_exists",
                    )
                )
                continue

            candidate = self._build_candidate(asset=asset, scan_ts=now_utc)
            if dry_run:
                created_count += 1
                items.append(
                    CandidateRefreshItem(
                        symbol=symbol,
                        action="would_create",
                        reason="eligible_for_refresh",
                        signal_id=None,
                    )
                )
                continue

            self._session.add(candidate)
            self._session.flush()
            created_count += 1
            items.append(
                CandidateRefreshItem(
                    symbol=symbol,
                    action="created",
                    reason="created_fresh_candidate",
                    signal_id=str(candidate.id),
                )
            )

        return {
            "created_count": created_count,
            "skipped_count": skipped_count,
            "candidates": [
                {
                    "symbol": item.symbol,
                    "action": item.action,
                    "reason": item.reason,
                    "signal_id": item.signal_id,
                }
                for item in items
            ],
        }

    def _load_assets_by_symbol(self, symbols: list[str]) -> dict[str, Asset]:
        rows = (
            self._session.execute(
                select(Asset).where(Asset.symbol.in_(symbols))
            )
            .scalars()
            .all()
        )
        return {asset.symbol.upper(): asset for asset in rows}

    def _has_recent_eligible_candidate(self, *, asset_id, cutoff: datetime) -> bool:
        stmt = (
            select(Signal.id)
            .join(Asset, Signal.asset_id == Asset.id)
            .where(Signal.asset_id == asset_id)
            .where(Signal.signal_status == SignalStatus.CANDIDATE)
            .where(Signal.scan_ts >= cutoff)
            .where(Signal.signal_score >= _QUEUE_MIN_SIGNAL_SCORE)
            .where(provider_filter(Signal.provider_name, include_visual_seed=False))
            .limit(1)
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        return existing is not None

    def _build_candidate(self, *, asset: Asset, scan_ts: datetime) -> Signal:
        return Signal(
            asset_id=asset.id,
            provider_name=self._provider_name,
            scan_ts=scan_ts,
            timeframe=_DEFAULT_TIMEFRAME,
            signal_status=SignalStatus.CANDIDATE,
            direction=TradeDirection.LONG,
            setup_type=SetupType.TREND_PULLBACK,
            regime=RegimeType.TREND,
            entry_min=50.0,
            entry_max=50.5,
            stop_price=49.0,
            target_price=52.0,
            confidence=_DEFAULT_CONFIDENCE,
            horizon_label=HorizonLabel.INTRADAY,
            catalyst_type=CatalystType.NONE,
            catalyst_score=0.6,
            catalyst_summary="paper candidate refresh",
            thesis=f"Paper refresh candidate for {asset.symbol}",
            invalidators_json=["refresh_only"],
            signal_score=_DEFAULT_SIGNAL_SCORE,
            raw_llm_json={"source": self._provider_name, "refresh": True},
        )

    @staticmethod
    def is_supported_asset_class(asset_class: AssetClass) -> bool:
        return asset_class in {AssetClass.EQUITY, AssetClass.ETF}
