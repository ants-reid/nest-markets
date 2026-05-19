"""MarketDataCoverageService — computes asset bar coverage from existing bars data.

MH-01: Data Centre Foundation.
Reads from the existing `bars` and `assets` tables only.
Does NOT create or modify any bar data.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.schemas.research_data import AssetCoverageItem, AssetCoverageResponse


class MarketDataCoverageService:
    """Calculate coverage metrics from existing bars without modifying data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_coverage(self) -> AssetCoverageResponse:
        """Build a full asset coverage response from existing bars table.

        Works with empty bars table (returns zero coverage) or populated table.
        """
        evaluated_at = datetime.now(UTC)

        # All active assets in the universe
        assets = self._session.execute(
            select(Asset).order_by(Asset.symbol)
        ).scalars().all()

        total_assets = len(assets)
        if total_assets == 0:
            return AssetCoverageResponse(
                evaluated_at=evaluated_at,
                total_assets=0,
                covered_assets=0,
                uncovered_assets=0,
                items=[],
            )

        # Aggregate bar stats per asset
        bar_stats: dict[str, dict[str, Any]] = self._aggregate_bar_stats()

        items: list[AssetCoverageItem] = []
        covered = 0
        for asset in assets:
            stats = bar_stats.get(str(asset.id))
            if stats:
                covered += 1
                item = AssetCoverageItem(
                    asset_symbol=asset.symbol,
                    asset_name=asset.name,
                    is_active=asset.is_active,
                    timeframes=stats["timeframes"],
                    total_bars=stats["total_bars"],
                    earliest_bar_ts=stats["earliest_bar_ts"],
                    latest_bar_ts=stats["latest_bar_ts"],
                    providers=stats["providers"],
                )
            else:
                item = AssetCoverageItem(
                    asset_symbol=asset.symbol,
                    asset_name=asset.name,
                    is_active=asset.is_active,
                    timeframes=[],
                    total_bars=0,
                    earliest_bar_ts=None,
                    latest_bar_ts=None,
                    providers=[],
                )
            items.append(item)

        return AssetCoverageResponse(
            evaluated_at=evaluated_at,
            total_assets=total_assets,
            covered_assets=covered,
            uncovered_assets=total_assets - covered,
            items=items,
        )

    def _aggregate_bar_stats(self) -> dict[str, dict[str, Any]]:
        """Return per-asset bar stats keyed by asset_id string."""
        # Aggregate totals and date span per asset
        rows = self._session.execute(
            select(
                Bar.asset_id,
                func.count(Bar.id).label("total_bars"),
                func.min(Bar.ts).label("earliest"),
                func.max(Bar.ts).label("latest"),
            ).group_by(Bar.asset_id)
        ).all()

        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            result[str(row.asset_id)] = {
                "total_bars": row.total_bars,
                "earliest_bar_ts": row.earliest,
                "latest_bar_ts": row.latest,
                "timeframes": [],
                "providers": [],
            }

        if not result:
            return result

        # Timeframes per asset
        tf_rows = self._session.execute(
            select(Bar.asset_id, Bar.timeframe).distinct()
        ).all()
        for row in tf_rows:
            key = str(row.asset_id)
            if key in result:
                result[key]["timeframes"].append(row.timeframe)

        # Providers per asset (source column)
        prov_rows = self._session.execute(
            select(Bar.asset_id, Bar.source).where(Bar.source.isnot(None)).distinct()
        ).all()
        for row in prov_rows:
            key = str(row.asset_id)
            if key in result:
                if row.source and row.source not in result[key]["providers"]:
                    result[key]["providers"].append(row.source)

        return result
