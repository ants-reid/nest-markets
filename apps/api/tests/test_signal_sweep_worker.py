"""Tests for SignalSweepWorker and its scheduler registration — QA-203/204/205."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.schedules.data_sync_scheduler import DataSyncScheduler
from app.workers.base_worker import BaseWorker
from app.workers.signal_sweep_worker import SignalSweepWorker, _build_feature_snapshot


# ---------------------------------------------------------------------------
# QA-203 — BaseWorker subclass contract
# ---------------------------------------------------------------------------


def test_signal_sweep_worker_is_base_worker():
    """SignalSweepWorker must extend BaseWorker (Gate 9)."""
    assert issubclass(SignalSweepWorker, BaseWorker)


def test_signal_sweep_worker_name():
    """worker_name must be 'signal_sweep'."""
    assert SignalSweepWorker.worker_name == "signal_sweep"


# ---------------------------------------------------------------------------
# QA-204 — Scheduler registration
# ---------------------------------------------------------------------------


def test_signal_sweep_registered_in_scheduler():
    """signal_sweep job must be registered in DataSyncScheduler."""
    scheduler = DataSyncScheduler()
    names = {j.name for j in scheduler.list_jobs()}
    assert "signal_sweep" in names


def test_signal_sweep_scheduler_cron_is_4h():
    """signal_sweep cron must run every 4 hours."""
    scheduler = DataSyncScheduler()
    job = next(j for j in scheduler.list_jobs() if j.name == "signal_sweep")
    assert "4" in job.cron  # 0 */4 * * *


def test_signal_sweep_scheduler_returns_worker_instance():
    """get_worker('signal_sweep') must return a SignalSweepWorker instance."""
    scheduler = DataSyncScheduler()
    worker = scheduler.get_worker("signal_sweep")
    assert isinstance(worker, SignalSweepWorker)


# ---------------------------------------------------------------------------
# QA-205 — Bar fetch integration (Polygon bars wired into sweep)
# ---------------------------------------------------------------------------


def _make_asset(symbol: str) -> MagicMock:
    a = MagicMock(spec=Asset)
    a.id = symbol
    a.symbol = symbol
    a.asset_class = AssetClass.FX
    a.is_active = True
    return a


def _make_bar(close: float = 1.08, volume: float = 1000.0) -> MagicMock:
    b = MagicMock()
    b.open = close - 0.002
    b.high = close + 0.005
    b.low = close - 0.005
    b.close = close
    b.volume = volume
    return b


def test_build_feature_snapshot_empty_bars():
    """_build_feature_snapshot returns bar_count=0 for empty list."""
    snap = _build_feature_snapshot([])
    assert snap == {"bar_count": 0}


def test_build_feature_snapshot_single_bar():
    """_build_feature_snapshot returns expected keys for one bar."""
    bar = _make_bar(close=1.0815)
    snap = _build_feature_snapshot([bar])
    assert snap["bar_count"] == 1
    assert snap["close"] == 1.0815
    assert "price_change_pct" in snap


def test_signal_sweep_execute_calls_polygon_per_asset():
    """execute() calls PolygonClient.get_bars once per active asset."""
    mock_client = MagicMock()
    mock_session = MagicMock()

    bar = _make_bar()
    mock_client.get_bars = AsyncMock(return_value=[bar, bar, bar])

    assets = [_make_asset("EURUSD"), _make_asset("GBPUSD")]
    mock_session.execute.return_value.scalars.return_value.all.return_value = assets

    mock_signal_output = MagicMock()
    mock_signal_output.should_trade = True

    with (
        patch("app.workers.signal_sweep_worker.SignalService") as mock_svc_cls,
        patch("app.workers.signal_sweep_worker.PersistenceSignalService") as mock_persist_cls,
    ):
        mock_svc = MagicMock()
        mock_svc.generate_signal = AsyncMock(return_value=mock_signal_output)
        mock_svc_cls.return_value = mock_svc

        mock_persist = MagicMock()
        mock_persist_cls.return_value = mock_persist

        worker = SignalSweepWorker(client=mock_client, session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert mock_client.get_bars.call_count == 2
    assert mock_persist.persist_signal.call_count == 2


def test_signal_sweep_execute_skips_empty_bars():
    """execute() skips assets that return no bars from Polygon."""
    mock_client = MagicMock()
    mock_session = MagicMock()

    mock_client.get_bars = AsyncMock(return_value=[])  # no bars

    assets = [_make_asset("EURUSD")]
    mock_session.execute.return_value.scalars.return_value.all.return_value = assets

    with (
        patch("app.workers.signal_sweep_worker.SignalService"),
        patch("app.workers.signal_sweep_worker.PersistenceSignalService") as mock_persist_cls,
    ):
        mock_persist = MagicMock()
        mock_persist_cls.return_value = mock_persist

        worker = SignalSweepWorker(client=mock_client, session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    mock_persist.persist_signal.assert_not_called()
    assert "0 signals generated" in result.message


def test_signal_sweep_execute_tolerates_per_asset_errors():
    """execute() continues with remaining assets when one raises an error."""
    mock_client = MagicMock()
    mock_session = MagicMock()

    bar = _make_bar()
    call_count = [0]

    async def _get_bars_side(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Polygon 429")
        return [bar, bar]

    mock_client.get_bars = _get_bars_side

    assets = [_make_asset("EURUSD"), _make_asset("GBPUSD")]
    mock_session.execute.return_value.scalars.return_value.all.return_value = assets

    mock_signal_output = MagicMock()

    with (
        patch("app.workers.signal_sweep_worker.SignalService") as mock_svc_cls,
        patch("app.workers.signal_sweep_worker.PersistenceSignalService"),
    ):
        mock_svc = MagicMock()
        mock_svc.generate_signal = AsyncMock(return_value=mock_signal_output)
        mock_svc_cls.return_value = mock_svc

        worker = SignalSweepWorker(client=mock_client, session=mock_session)
        result = worker.run()

    assert result.status == "ok"
    assert "errors" in result.message
    assert "EURUSD" in result.message
