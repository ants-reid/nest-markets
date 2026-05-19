"""MH-07 tests for Historical Replay Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.backtest_run import BacktestRun
from app.db.models.bar import Bar
from app.db.models.market_data_quality_report import MarketDataQualityReport
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.historical_replay_service import HistoricalReplayService, ReplayError


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():  # type: ignore[misc]
    schema_name = f"test_replay_{uuid4().hex}"

    admin_conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_conn.close()

    conn = engine.connect()
    conn.execute(text(f'SET search_path TO "{schema_name}"'))
    conn.commit()
    Base.metadata.create_all(bind=conn)

    session = SessionLocal(bind=conn)
    try:
        yield session
    finally:
        session.close()
        conn.close()
        cleanup = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        cleanup.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        cleanup.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:  # type: ignore[misc]
    def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ── Seed helpers ───────────────────────────────────────────────────────────

def _make_asset(session: Session, symbol: str = "AAPL") -> Asset:
    asset = Asset(
        symbol=symbol,
        name=symbol,
        asset_class=AssetClass.EQUITY,
        is_active=True,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _make_bars(
    session: Session,
    asset: Asset,
    timeframe: str = "1d",
    count: int = 5,
    start: datetime | None = None,
) -> list[Bar]:
    if start is None:
        start = datetime(2024, 1, 2, tzinfo=timezone.utc)
    bars = []
    for i in range(count):
        ts = start.replace(day=start.day + i)
        bar = Bar(
            asset_id=asset.id,
            timeframe=timeframe,
            ts=ts,
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("102.00"),
            volume=Decimal("1000000"),
        )
        session.add(bar)
    session.commit()
    return bars


def _make_quality_report(
    session: Session,
    symbol: str,
    timeframe: str = "1d",
    approved: bool = True,
    quality_score: float = 0.95,
) -> MarketDataQualityReport:
    report = MarketDataQualityReport(
        asset_symbol=symbol,
        timeframe=timeframe,
        evaluated_at=datetime.now(tz=timezone.utc),
        actual_bars=10,
        total_bars=10,
        approved_for_backtest=approved,
        quality_score=quality_score,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def _make_run(
    session: Session,
    assets: list[str] | None = None,
    timeframes: list[str] | None = None,
    status: str = "queued",
) -> BacktestRun:
    run = BacktestRun(
        name="Test Run",
        status=status,
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
        requested_assets={"assets": assets or ["AAPL"]},
        requested_timeframes={"timeframes": timeframes or ["1d"]},
        strategy_config_ids={"config_ids": []},
        starting_capital=Decimal("10000"),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


# ── Tests ──────────────────────────────────────────────────────────────────

def test_replay_route_exists() -> None:
    """Smoke: replay route is registered in the app."""
    paths = {r.path for r in app.routes}
    assert "/strategy-lab/backtests/{backtest_id}/replay" in paths


def test_replay_fails_run_not_found(client: TestClient) -> None:
    response = client.post(
        f"/strategy-lab/backtests/{uuid4()}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_replay_fails_no_bars(db_session: Session, client: TestClient) -> None:
    """Replay returns failed status when no bars exist for the assets."""
    _make_asset(db_session, "AAPL")
    _make_quality_report(db_session, "AAPL", approved=True)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["total_candles_loaded"] == 0


def test_replay_blocks_unapproved_data_by_default(
    db_session: Session, client: TestClient
) -> None:
    """Default allow_unapproved_data=false must block unapproved asset."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=5)
    _make_quality_report(db_session, "AAPL", approved=False, quality_score=0.4)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["total_candles_loaded"] == 0
    assert "AAPL/1d" in data["skipped_assets"]


def test_replay_proceeds_with_allow_unapproved(
    db_session: Session, client: TestClient
) -> None:
    """allow_unapproved_data=true should proceed even with no approval."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=5)
    _make_quality_report(db_session, "AAPL", approved=False, quality_score=0.4)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": True, "max_candles": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_candles_loaded"] == 5
    assert "AAPL" in data["assets_replayed"]
    assert len(data["warnings"]) > 0  # warning should be present for unapproved


def test_replay_proceeds_with_approved_data(
    db_session: Session, client: TestClient
) -> None:
    """Replay should complete cleanly with approved data and bars."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=10)
    _make_quality_report(db_session, "AAPL", approved=True, quality_score=0.97)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_candles_loaded"] == 10
    assert data["first_timestamp"] is not None
    assert data["last_timestamp"] is not None
    assert "MH-08" in data["message"]


def test_replay_stores_result_summary(db_session: Session, client: TestClient) -> None:
    """result_summary on the BacktestRun should be populated after replay."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=5)
    _make_quality_report(db_session, "AAPL", approved=True)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    db_session.refresh(run)
    assert run.result_summary is not None
    assert run.result_summary.get("status") == "completed"
    assert run.result_summary.get("total_candles_loaded") == 5


def test_replay_updates_backtest_run_status(
    db_session: Session, client: TestClient
) -> None:
    """BacktestRun.status should be 'completed' after a successful replay."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=5)
    _make_quality_report(db_session, "AAPL", approved=True)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    assert run.status == "queued"
    client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    db_session.refresh(run)
    assert run.status == "completed"
    assert run.started_at is not None
    assert run.completed_at is not None


def test_replay_does_not_create_mock_trades(
    db_session: Session, client: TestClient
) -> None:
    """Replay must not generate any mock trades."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=5)
    _make_quality_report(db_session, "AAPL", approved=True)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )

    trades_resp = client.get(f"/strategy-lab/backtests/{run.id}/trades")
    assert trades_resp.status_code == 200
    assert trades_resp.json()["total"] == 0


def test_replay_respects_max_candles(db_session: Session, client: TestClient) -> None:
    """max_candles should cap the number of candles loaded."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=10)
    _make_quality_report(db_session, "AAPL", approved=True)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"])

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_candles_loaded"] == 3


def test_replay_rejects_non_queued_run(db_session: Session, client: TestClient) -> None:
    """Attempting to replay a run that is already completed should fail."""
    asset = _make_asset(db_session, "AAPL")
    _make_bars(db_session, asset, count=5)
    _make_quality_report(db_session, "AAPL", approved=True)
    run = _make_run(db_session, assets=["AAPL"], timeframes=["1d"], status="completed")

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    assert response.status_code == 400
    assert "completed" in response.json()["detail"]


def test_replay_treats_missing_quality_report_as_unapproved(
    db_session: Session, client: TestClient
) -> None:
    """No quality report = unapproved by default."""
    asset = _make_asset(db_session, "MSFT")
    _make_bars(db_session, asset, count=5)
    # deliberately no quality report
    run = _make_run(db_session, assets=["MSFT"], timeframes=["1d"])

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": False, "max_candles": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert any("No quality report" in w for w in data["warnings"])


def test_replay_no_report_proceeds_with_override(
    db_session: Session, client: TestClient
) -> None:
    """allow_unapproved_data=true should bypass missing report."""
    asset = _make_asset(db_session, "MSFT")
    _make_bars(db_session, asset, count=5)
    run = _make_run(db_session, assets=["MSFT"], timeframes=["1d"])

    response = client.post(
        f"/strategy-lab/backtests/{run.id}/replay",
        json={"allow_unapproved_data": True, "max_candles": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_candles_loaded"] == 5


# ── Service unit tests ─────────────────────────────────────────────────────

def test_service_replay_raises_for_unknown_run(db_session: Session) -> None:
    svc = HistoricalReplayService(db_session)
    with pytest.raises(ReplayError, match="not found"):
        svc.replay(uuid4())


def test_service_extract_list_handles_envelope() -> None:
    assert HistoricalReplayService._extract_list({"assets": ["AAPL", "MSFT"]}, "assets") == ["AAPL", "MSFT"]
    assert HistoricalReplayService._extract_list(["A", "B"], "assets") == ["A", "B"]
    assert HistoricalReplayService._extract_list(None, "assets") == []
