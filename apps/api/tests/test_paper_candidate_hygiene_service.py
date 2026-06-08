from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.db.enums import AssetClass, SignalStatus, SetupType, TradeDirection
from app.db.models.asset import Asset
from app.db.models.signal import Signal
from app.db.session import SessionLocal
from app.services.paper_candidate_hygiene_service import PaperCandidateHygieneService


@pytest.fixture()
def cleanup_hygiene_rows():
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


def _insert_asset(symbol: str) -> Asset:
    with SessionLocal() as session:
        asset = Asset(
            symbol=symbol,
            name=f"Hygiene {symbol}",
            asset_class=AssetClass.EQUITY,
            exchange="TEST",
            is_active=True,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset


def _insert_signal(
    *,
    symbol: str,
    provider_name: str,
    signal_status: SignalStatus,
    age_hours: int,
    score: float,
) -> str:
    with SessionLocal() as session:
        asset = session.query(Asset).filter(Asset.symbol == symbol).one()
        signal = Signal(
            asset_id=asset.id,
            provider_name=provider_name,
            scan_ts=datetime.now(UTC) - timedelta(hours=age_hours),
            timeframe="1h",
            signal_status=signal_status,
            direction=TradeDirection.LONG,
            setup_type=SetupType.TREND_PULLBACK,
            signal_score=score,
            confidence=0.9,
        )
        session.add(signal)
        session.commit()
        session.refresh(signal)
        return str(signal.id)


def _status_by_id(signal_id: str) -> SignalStatus:
    with SessionLocal() as session:
        signal = session.get(Signal, signal_id)
        assert signal is not None
        return signal.signal_status


def test_hygiene_dry_run_identifies_stale_candidates(cleanup_hygiene_rows):
    symbol = f"HY{uuid.uuid4().hex[:6].upper()}"
    cleanup_hygiene_rows.append(symbol)
    _insert_asset(symbol)
    stale_id = _insert_signal(
        symbol=symbol,
        provider_name="paper_normal_refresh",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=9,
        score=80.0,
    )

    with SessionLocal() as session:
        result = PaperCandidateHygieneService(session).run(
            dry_run=True,
            apply=False,
            max_age_hours=8,
            keep_per_symbol=1,
            allowlist_symbols=[symbol],
        )

    assert result["stale_count"] >= 1
    assert result["would_update_count"] >= 1
    assert any(item["signal_id"] == stale_id for item in result["affected_candidates"])


def test_hygiene_dry_run_identifies_duplicate_same_symbol_candidates(cleanup_hygiene_rows):
    symbol = f"HY{uuid.uuid4().hex[:6].upper()}"
    cleanup_hygiene_rows.append(symbol)
    _insert_asset(symbol)
    newest_id = _insert_signal(
        symbol=symbol,
        provider_name="manual_paper_normal_seed",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=1,
        score=99.0,
    )
    older_id = _insert_signal(
        symbol=symbol,
        provider_name="manual_paper_normal_seed",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=2,
        score=70.0,
    )

    with SessionLocal() as session:
        result = PaperCandidateHygieneService(session).run(
            dry_run=True,
            apply=False,
            max_age_hours=8,
            keep_per_symbol=1,
            allowlist_symbols=[symbol],
        )

    assert result["duplicate_count"] >= 1
    affected_ids = {item["signal_id"] for item in result["affected_candidates"]}
    assert older_id in affected_ids
    assert newest_id not in affected_ids


def test_hygiene_dry_run_identifies_outside_allowlist_candidates(cleanup_hygiene_rows):
    allowed_symbol = f"HY{uuid.uuid4().hex[:6].upper()}"
    blocked_symbol = f"HY{uuid.uuid4().hex[:6].upper()}"
    cleanup_hygiene_rows.extend([allowed_symbol, blocked_symbol])
    _insert_asset(allowed_symbol)
    _insert_asset(blocked_symbol)

    _insert_signal(
        symbol=allowed_symbol,
        provider_name="manual_scheduler_seed",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=1,
        score=90.0,
    )
    blocked_id = _insert_signal(
        symbol=blocked_symbol,
        provider_name="manual_scheduler_seed",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=1,
        score=91.0,
    )

    with SessionLocal() as session:
        result = PaperCandidateHygieneService(session).run(
            dry_run=True,
            apply=False,
            max_age_hours=8,
            keep_per_symbol=1,
            allowlist_symbols=[allowed_symbol],
        )

    assert result["outside_allowlist_count"] >= 1
    assert any(item["signal_id"] == blocked_id for item in result["affected_candidates"])


def test_hygiene_apply_updates_only_paper_test_candidate_rows(cleanup_hygiene_rows):
    symbol = f"HY{uuid.uuid4().hex[:6].upper()}"
    cleanup_hygiene_rows.append(symbol)
    _insert_asset(symbol)

    paper_target_id = _insert_signal(
        symbol=symbol,
        provider_name="paper_normal_refresh",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=12,
        score=75.0,
    )
    non_paper_id = _insert_signal(
        symbol=symbol,
        provider_name="non_paper_provider",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=12,
        score=76.0,
    )

    with SessionLocal() as session:
        result = PaperCandidateHygieneService(session).run(
            dry_run=False,
            apply=True,
            max_age_hours=8,
            keep_per_symbol=1,
            allowlist_symbols=[symbol],
        )
        session.commit()

    assert result["updated_count"] >= 1
    assert _status_by_id(paper_target_id) == SignalStatus.EXPIRED
    assert _status_by_id(non_paper_id) == SignalStatus.CANDIDATE


def test_hygiene_does_not_touch_submitted_signals(cleanup_hygiene_rows):
    symbol = f"HY{uuid.uuid4().hex[:6].upper()}"
    cleanup_hygiene_rows.append(symbol)
    _insert_asset(symbol)

    paper_submitted_id = _insert_signal(
        symbol=symbol,
        provider_name="paper_normal_refresh",
        signal_status=SignalStatus.PAPER_SUBMITTED,
        age_hours=12,
        score=60.0,
    )
    live_submitted_id = _insert_signal(
        symbol=symbol,
        provider_name="paper_normal_refresh",
        signal_status=SignalStatus.LIVE_SUBMITTED,
        age_hours=12,
        score=60.0,
    )

    with SessionLocal() as session:
        result = PaperCandidateHygieneService(session).run(
            dry_run=False,
            apply=True,
            max_age_hours=8,
            keep_per_symbol=1,
            allowlist_symbols=[symbol],
        )
        session.commit()

    assert result["updated_count"] == 0
    assert _status_by_id(paper_submitted_id) == SignalStatus.PAPER_SUBMITTED
    assert _status_by_id(live_submitted_id) == SignalStatus.LIVE_SUBMITTED


def test_hygiene_does_not_touch_live_non_paper_provider_rows(cleanup_hygiene_rows):
    symbol = f"HY{uuid.uuid4().hex[:6].upper()}"
    cleanup_hygiene_rows.append(symbol)
    _insert_asset(symbol)

    non_paper_candidate_id = _insert_signal(
        symbol=symbol,
        provider_name="live_candidate_seed",
        signal_status=SignalStatus.CANDIDATE,
        age_hours=24,
        score=55.0,
    )

    with SessionLocal() as session:
        result = PaperCandidateHygieneService(session).run(
            dry_run=False,
            apply=True,
            max_age_hours=8,
            keep_per_symbol=1,
            allowlist_symbols=[symbol],
        )
        session.commit()

    assert result["updated_count"] == 0
    assert _status_by_id(non_paper_candidate_id) == SignalStatus.CANDIDATE
