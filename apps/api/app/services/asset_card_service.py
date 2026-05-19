"""MH-COCKPIT-02-A — Read-only asset-card snapshot service.

Computes a small "market quality" payload per asset from the existing
``assets`` and ``bars`` tables. Intended for the operator Cockpit to surface
data freshness/quality at a glance.

Drift-lock guarantee:
* Pure SELECT over existing tables — no INSERT/UPDATE/DELETE.
* No provider call, no LLM call.
* The derived ``quality`` flag is an operator hint only; the trading path
  never reads from this service.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.bar import Bar


# Quality thresholds. Operator hint only; never feeds trading.
_FRESH_AGE_SECONDS = 60 * 60          # < 1 hour → fresh
_STALE_AGE_SECONDS = 60 * 60 * 24     # < 24h → stale, else "very_stale"
_RECENT_BAR_LIMIT = 30                # bars used for vol/volume averages
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _quality_flag(age_seconds: Optional[float], bar_count: int) -> str:
    if bar_count == 0 or age_seconds is None:
        return "no_data"
    if age_seconds < _FRESH_AGE_SECONDS:
        return "fresh"
    if age_seconds < _STALE_AGE_SECONDS:
        return "stale"
    return "very_stale"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_market_quality(
    session: Session,
    asset: Asset,
    *,
    now_utc: datetime,
) -> Dict[str, Any]:
    stmt = (
        select(Bar)
        .where(Bar.asset_id == asset.id)
        .order_by(desc(Bar.ts))
        .limit(_RECENT_BAR_LIMIT)
    )
    bars: List[Bar] = list(session.execute(stmt).scalars().all())

    if not bars:
        return {
            "bar_count": 0,
            "last_close": None,
            "last_bar_ts": None,
            "bars_age_seconds": None,
            "recent_avg_volume": None,
            "recent_volatility": None,
            "timeframe": None,
            "quality": "no_data",
        }

    latest = bars[0]
    last_close = _safe_float(latest.close)
    last_bar_ts: Optional[datetime] = latest.ts
    age_seconds: Optional[float] = None
    if last_bar_ts is not None:
        if last_bar_ts.tzinfo is None:
            last_bar_ts = last_bar_ts.replace(tzinfo=timezone.utc)
        age_seconds = max(0.0, (now_utc - last_bar_ts).total_seconds())

    closes = [_safe_float(b.close) for b in bars]
    closes_clean = [c for c in closes if c is not None]
    volatility: Optional[float] = None
    if len(closes_clean) >= 2:
        try:
            volatility = statistics.pstdev(closes_clean)
        except statistics.StatisticsError:
            volatility = None

    volumes = [_safe_float(b.volume) for b in bars]
    volumes_clean = [v for v in volumes if v is not None]
    avg_volume = (sum(volumes_clean) / len(volumes_clean)) if volumes_clean else None

    return {
        "bar_count": len(bars),
        "last_close": last_close,
        "last_bar_ts": last_bar_ts.isoformat() if last_bar_ts else None,
        "bars_age_seconds": age_seconds,
        "recent_avg_volume": avg_volume,
        "recent_volatility": volatility,
        "timeframe": latest.timeframe,
        "quality": _quality_flag(age_seconds, len(bars)),
    }


def get_asset_card_snapshot(
    session: Session,
    *,
    asset_class: Optional[AssetClass] = None,
    active_only: bool = True,
    limit: int = _DEFAULT_LIMIT,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return a snapshot of asset cards with derived market-quality metrics.

    Pure read. Caller controls ``limit`` (capped at ``_MAX_LIMIT``).
    """

    if limit < 1:
        limit = 1
    if limit > _MAX_LIMIT:
        limit = _MAX_LIMIT
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    stmt = select(Asset)
    if active_only:
        stmt = stmt.where(Asset.is_active.is_(True))
    if asset_class is not None:
        stmt = stmt.where(Asset.asset_class == asset_class)
    stmt = stmt.order_by(Asset.symbol).limit(limit)

    assets: List[Asset] = list(session.execute(stmt).scalars().all())

    cards: List[Dict[str, Any]] = []
    for asset in assets:
        cards.append(
            {
                "id": str(asset.id),
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_class": asset.asset_class.value if hasattr(asset.asset_class, "value") else str(asset.asset_class),
                "exchange": asset.exchange,
                "sector": asset.sector,
                "industry": asset.industry,
                "is_active": bool(asset.is_active),
                "market_quality": _compute_market_quality(session, asset, now_utc=now_utc),
            }
        )

    return {
        "as_of_utc": now_utc.isoformat(),
        "count": len(cards),
        "limit": limit,
        "filters": {
            "asset_class": asset_class.value if asset_class is not None and hasattr(asset_class, "value") else asset_class,
            "active_only": active_only,
        },
        "advisory": (
            "Operator hint only. Market-quality flags are derived from "
            "available bar data and never feed the trading path."
        ),
        "items": cards,
    }


# MH-COCKPIT-11-A — read-only single-asset detail.

class AssetCardNotFoundError(LookupError):
    """Raised when the requested asset id has no matching row."""


_DEFAULT_DETAIL_BAR_LIMIT = 30
_MAX_DETAIL_BAR_LIMIT = 200


def _serialize_recent_bar(bar: Bar) -> Dict[str, Any]:
    ts = bar.ts
    if ts is not None and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return {
        "ts": ts.isoformat() if ts is not None else None,
        "timeframe": bar.timeframe,
        "open": _safe_float(bar.open),
        "high": _safe_float(bar.high),
        "low": _safe_float(bar.low),
        "close": _safe_float(bar.close),
        "volume": _safe_float(bar.volume),
        "vwap": _safe_float(bar.vwap),
        "source": bar.source,
    }


def get_asset_card_detail(
    session: Session,
    asset_id: Any,
    *,
    recent_bars_limit: int = _DEFAULT_DETAIL_BAR_LIMIT,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return a single asset's card payload + a recent-bars list.

    Pure read. Raises ``AssetCardNotFoundError`` if the id does not match
    any asset row.
    """
    if recent_bars_limit < 1:
        recent_bars_limit = 1
    if recent_bars_limit > _MAX_DETAIL_BAR_LIMIT:
        recent_bars_limit = _MAX_DETAIL_BAR_LIMIT
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    asset = session.get(Asset, asset_id)
    if asset is None:
        raise AssetCardNotFoundError(f"asset_id not found: {asset_id}")

    bars_stmt = (
        select(Bar)
        .where(Bar.asset_id == asset.id)
        .order_by(desc(Bar.ts))
        .limit(recent_bars_limit)
    )
    recent_bars: List[Bar] = list(session.execute(bars_stmt).scalars().all())

    return {
        "as_of_utc": now_utc.isoformat(),
        "advisory": (
            "Operator hint only. Market-quality flags are derived from "
            "available bar data and never feed the trading path."
        ),
        "recent_bars_limit": recent_bars_limit,
        "asset": {
            "id": str(asset.id),
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_class": asset.asset_class.value if hasattr(asset.asset_class, "value") else str(asset.asset_class),
            "base_currency": asset.base_currency,
            "quote_currency": asset.quote_currency,
            "exchange": asset.exchange,
            "sector": asset.sector,
            "industry": asset.industry,
            "is_active": bool(asset.is_active),
        },
        "market_quality": _compute_market_quality(session, asset, now_utc=now_utc),
        "recent_bars": [_serialize_recent_bar(b) for b in recent_bars],
    }
