from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.db.enums import AssetClass, SignalStatus, TradeDirection, SetupType
from app.db.models.asset import Asset
from app.db.models.signal import Signal
from app.db.session import SessionLocal
from app.services.opportunity_ranker_service import OpportunityRankerService
from app.services.paper_candidate_refresh_service import PaperCandidateRefreshService


@pytest.fixture()
def cleanup_refresh_rows():
    created_symbols: list[str] = []
    yield created_symbols
    with SessionLocal() as session:
        if created_symbols:
            assets = session.query(Asset).filter(Asset.symbol.in_(created_symbols)).all()
            asset_ids = [asset.id for asset in assets]
            if asset_ids:
                session.query(Signal).filter(Signal.asset_id.in_(asset_ids)).delete(synchronize_session=False)
            session.query(Asset).filter(Asset.symbol.in_(created_symbols)).delete(synchronize_session=False)
            session.commit()


def _insert_asset(symbol: str) -> None:
    with SessionLocal() as session:
        session.add(
            Asset(
                symbol=symbol,
                name=f"Refresh {symbol}",
                asset_class=AssetClass.EQUITY,
                exchange="TEST",
                is_active=True,
            )
        )
        session.commit()


def _insert_recent_candidate(symbol: str) -> None:
    with SessionLocal() as session:
        asset = session.query(Asset).filter(Asset.symbol == symbol).one()
        session.add(
            Signal(
                asset_id=asset.id,
                provider_name="manual_paper_normal_seed",
                scan_ts=datetime.now(UTC) - timedelta(minutes=5),
                timeframe="1h",
                signal_status=SignalStatus.CANDIDATE,
                direction=TradeDirection.LONG,
                setup_type=SetupType.TREND_PULLBACK,
                signal_score=96.0,
                confidence=0.92,
            )
        )
        session.commit()


def test_refresh_creates_candidates_when_queue_empty(cleanup_refresh_rows):
    symbol_a = f"RF{uuid.uuid4().hex[:6].upper()}"
    symbol_b = f"RF{uuid.uuid4().hex[:6].upper()}"
    cleanup_refresh_rows.extend([symbol_a, symbol_b])
    _insert_asset(symbol_a)
    _insert_asset(symbol_b)

    with SessionLocal() as session:
        service = PaperCandidateRefreshService(session)
        result = service.refresh(symbols=[symbol_a, symbol_b], dry_run=False)
        session.commit()

    assert result["created_count"] == 2
    assert result["skipped_count"] == 0
    assert {item["action"] for item in result["candidates"]} == {"created"}


def test_refresh_skips_recent_eligible_candidates(cleanup_refresh_rows):
    symbol = f"RF{uuid.uuid4().hex[:6].upper()}"
    cleanup_refresh_rows.append(symbol)
    _insert_asset(symbol)
    _insert_recent_candidate(symbol)

    with SessionLocal() as session:
        service = PaperCandidateRefreshService(session)
        result = service.refresh(symbols=[symbol], dry_run=False)
        session.commit()

    assert result["created_count"] == 0
    assert result["skipped_count"] == 1
    assert result["candidates"][0]["reason"] == "recent_eligible_candidate_exists"


def test_refresh_output_shape_is_ranker_eligible(cleanup_refresh_rows):
    symbol = f"RF{uuid.uuid4().hex[:6].upper()}"
    cleanup_refresh_rows.append(symbol)
    _insert_asset(symbol)

    with SessionLocal() as session:
        service = PaperCandidateRefreshService(session)
        result = service.refresh(symbols=[symbol], dry_run=False)
        session.commit()

    assert result["created_count"] == 1

    with SessionLocal() as session:
        ranked = OpportunityRankerService(session).rank(limit=5, recency_hours=8)

    assert any(item.asset == symbol for item in ranked)
