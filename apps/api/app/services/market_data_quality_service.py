"""MarketDataQualityService — MH-03 quality reporting and recalculation."""

from __future__ import annotations

from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.bar import Bar
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.models.quality_review_audit import QualityReviewAudit
from app.schemas.research_data import (
    OutlierItem,
    OutlierListResponse,
    OutlierReviewRequest,
    OutlierReviewResponse,
    QualityRecalculateRequest,
    QualityRecalculateResponse,
    QualityRecalculateItem,
    QualityReportItem,
    QualityReportResponse,
    QualityReviewAuditEntry,
    QualityReviewAuditResponse,
    UnreviewedSummaryResponse,
)
from app.services.data_quality_engine import DataQualityEngine


class MarketDataQualityService:
    """Generate and persist deterministic quality summaries."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._engine = DataQualityEngine(session)

    def get_quality_report(self, asset_symbol: str | None = None) -> QualityReportResponse:
        """Build a quality report for all (or one) asset's bars.

        Works with empty bars table — returns empty items list, no error.
        """
        evaluated_at = datetime.now(UTC)

        query = (
            select(Asset.symbol, Bar.timeframe, Bar.source)
            .join(Bar, Bar.asset_id == Asset.id)
            .distinct()
            .order_by(Asset.symbol, Bar.timeframe)
        )
        if asset_symbol:
            query = query.where(Asset.symbol == asset_symbol)

        combos = self._session.execute(query).all()

        if not combos:
            return QualityReportResponse(
                evaluated_at=evaluated_at,
                total_items=0,
                items=[],
            )

        items: list[QualityReportItem] = []
        for symbol, timeframe, provider in combos:
            metrics = self._engine.calculate(
                asset_symbol=symbol,
                timeframe=timeframe,
                provider=provider,
            )
            items.append(QualityReportItem(
                asset_symbol=metrics.asset_symbol,
                timeframe=metrics.timeframe,
                provider=metrics.provider,
                expected_bars=metrics.expected_bars,
                actual_bars=metrics.actual_bars,
                total_bars=metrics.total_bars,
                completeness_pct=metrics.completeness_pct,
                missing_pct=metrics.missing_pct,
                missing_bars=metrics.missing_bars,
                duplicate_bars=metrics.duplicate_bars,
                bad_price_bars=metrics.bad_price_bars,
                suspicious_spike_bars=metrics.suspicious_spike_bars,
                stale_bars=0,
                earliest_bar_ts=metrics.earliest_bar_ts,
                latest_bar_ts=metrics.latest_bar_ts,
                quality_score=metrics.quality_score,
                approved_for_backtest=metrics.approved_for_backtest,
                notes=metrics.notes,
            ))

        return QualityReportResponse(
            evaluated_at=evaluated_at,
            total_items=len(items),
            items=items,
        )

    def recalculate_quality(self, request: QualityRecalculateRequest) -> QualityRecalculateResponse:
        """Recalculate quality and persist reports/gaps/coverage snapshots."""
        items: list[QualityRecalculateItem] = []
        failed = 0

        try:
            metrics_list = self._engine.recalculate_and_persist(
                assets=[a.upper() for a in request.assets],
                timeframes=request.timeframes,
                providers=request.providers,
            )
        except Exception:  # noqa: BLE001
            return QualityRecalculateResponse(total=0, succeeded=0, failed=1, items=[])

        for metrics in metrics_list:
            items.append(
                QualityRecalculateItem(
                    asset_symbol=metrics.asset_symbol,
                    timeframe=metrics.timeframe,
                    provider=metrics.provider,
                    quality_score=metrics.quality_score,
                    completeness_pct=metrics.completeness_pct,
                    missing_bars=metrics.missing_bars,
                    duplicate_bars=metrics.duplicate_bars,
                    bad_price_bars=metrics.bad_price_bars,
                    suspicious_spike_bars=metrics.suspicious_spike_bars,
                    approved_for_backtest=metrics.approved_for_backtest,
                    gap_count=len(metrics.gaps),
                    notes=metrics.notes,
                )
            )

        return QualityRecalculateResponse(
            total=len(items),
            succeeded=len(items),
            failed=failed,
            items=items,
        )

    # ── MH-12 ────────────────────────────────────────────────────────────

    def list_outliers(
        self,
        min_spikes: int = 0,
        max_quality_score: float | None = None,
        review_status: str | None = None,
        asset: str | None = None,
        provider: str | None = None,
        timeframe: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> OutlierListResponse:
        """Return persisted quality reports that are flagged as potential outliers.

        A report is an outlier if it has suspicious_spike_bars > 0 OR
        quality_score < 90.0 (i.e. not approved for backtest).
        Optionally filter by review_status, asset, provider, timeframe.
        """
        query = (
            select(MarketDataQualityReport)
            .where(
                or_(
                    MarketDataQualityReport.suspicious_spike_bars > min_spikes,
                    MarketDataQualityReport.quality_score < (max_quality_score or 90.0),
                )
            )
            .order_by(MarketDataQualityReport.evaluated_at.desc())
        )
        if review_status:
            query = query.where(MarketDataQualityReport.review_status == review_status)
        if asset:
            query = query.where(MarketDataQualityReport.asset_symbol == asset.upper())
        if provider:
            query = query.where(MarketDataQualityReport.provider == provider)
        if timeframe:
            query = query.where(MarketDataQualityReport.timeframe == timeframe)

        total_query = query.with_only_columns(MarketDataQualityReport.id)  # type: ignore[arg-type]
        total = len(self._session.execute(total_query).all())

        rows = self._session.execute(query.limit(limit).offset(offset)).scalars().all()
        items = [
            OutlierItem(
                id=row.id,
                asset_symbol=row.asset_symbol,
                timeframe=row.timeframe,
                provider=row.provider,
                quality_score=row.quality_score,
                approved_for_backtest=row.approved_for_backtest,
                suspicious_spike_bars=row.suspicious_spike_bars,
                bad_price_bars=row.bad_price_bars,
                missing_bars=row.missing_bars,
                completeness_pct=row.completeness_pct,
                total_bars=row.total_bars,
                evaluated_at=row.evaluated_at,
                review_status=row.review_status,  # type: ignore[arg-type]
                review_notes=row.review_notes,
                reviewed_by=row.reviewed_by,
                reviewed_at=row.reviewed_at,
            )
            for row in rows
        ]
        return OutlierListResponse(total=total, items=items)

    def review_outlier(
        self,
        report_id: UUID,
        request: OutlierReviewRequest,
    ) -> OutlierReviewResponse | None:
        """Set triage review_status and optional notes on a quality report.

        Also writes an audit entry and updates reviewed_by / reviewed_at.
        Returns None if the report does not exist.
        """
        row = self._session.get(MarketDataQualityReport, report_id)
        if row is None:
            return None

        now = datetime.now(UTC)
        previous_status = row.review_status

        row.review_status = request.review_status
        row.review_notes = request.review_notes
        row.reviewed_by = request.reviewed_by
        row.reviewed_at = now

        audit = QualityReviewAudit(
            report_id=str(report_id),
            asset_symbol=row.asset_symbol,
            timeframe=row.timeframe,
            provider=row.provider,
            previous_status=previous_status,
            new_status=request.review_status,
            review_notes=request.review_notes,
            reviewed_by=request.reviewed_by,
            reviewed_at=now,
        )
        self._session.add(audit)
        self._session.commit()
        self._session.refresh(row)
        return OutlierReviewResponse(
            id=row.id,
            asset_symbol=row.asset_symbol,
            timeframe=row.timeframe,
            review_status=row.review_status,  # type: ignore[return-value]
            review_notes=row.review_notes,
            reviewed_by=row.reviewed_by,
            reviewed_at=row.reviewed_at,
        )

    def get_audit_trail(
        self,
        report_id: UUID,
    ) -> QualityReviewAuditResponse:
        """Return the full audit trail for a quality report, newest first."""
        rows = (
            self._session.execute(
                select(QualityReviewAudit)
                .where(QualityReviewAudit.report_id == str(report_id))
                .order_by(QualityReviewAudit.reviewed_at.desc())
            )
            .scalars()
            .all()
        )
        entries = [
            QualityReviewAuditEntry(
                id=r.id,
                report_id=r.report_id,
                asset_symbol=r.asset_symbol,
                timeframe=r.timeframe,
                provider=r.provider,
                previous_status=r.previous_status,
                new_status=r.new_status,
                review_notes=r.review_notes,
                reviewed_by=r.reviewed_by,
                reviewed_at=r.reviewed_at,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return QualityReviewAuditResponse(total=len(entries), entries=entries)

    def get_unreviewed_summary(self) -> UnreviewedSummaryResponse:
        """Return counts of outlier quality reports by review_status."""
        base_query = select(MarketDataQualityReport).where(
            or_(
                MarketDataQualityReport.suspicious_spike_bars > 0,
                MarketDataQualityReport.quality_score < 90.0,
            )
        )
        all_rows = self._session.execute(base_query).scalars().all()

        by_status: dict[str, int] = {}
        for row in all_rows:
            status = row.review_status or "unreviewed"
            by_status[status] = by_status.get(status, 0) + 1

        total = len(all_rows)
        unreviewed = by_status.get("unreviewed", 0)
        reviewed = total - unreviewed

        return UnreviewedSummaryResponse(
            total_flagged=total,
            unreviewed=unreviewed,
            reviewed=reviewed,
            by_status=by_status,
        )
