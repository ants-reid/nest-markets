from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.data_sync_worker import DataSyncWorker, _is_seeded_test_symbol


def _asset(symbol: str) -> MagicMock:
    a = MagicMock()
    a.symbol = symbol
    return a


def test_seeded_symbol_filter_matches_expected_prefixes() -> None:
    assert _is_seeded_test_symbol("DUP34A3") is True
    assert _is_seeded_test_symbol("TEST4464") is True
    assert _is_seeded_test_symbol("TSTX2AD1") is True

    assert _is_seeded_test_symbol("AAPL") is False
    assert _is_seeded_test_symbol("MSFT") is False
    assert _is_seeded_test_symbol("NVDA") is False
    assert _is_seeded_test_symbol("SPY") is False
    assert _is_seeded_test_symbol("QQQ") is False


def test_execute_skips_seeded_symbols_and_syncs_real_assets() -> None:
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = [
        _asset("DUP34A3"),
        _asset("TEST4464"),
        _asset("TSTX2AD1"),
        _asset("AAPL"),
        _asset("MSFT"),
    ]

    service = MagicMock()
    service.ingest_bars = AsyncMock(return_value=5)

    with patch("app.workers.data_sync_worker.MarketDataService", return_value=service):
        worker = DataSyncWorker(client=MagicMock(), session=session)
        result = worker.execute()

    synced_symbols = [call.args[0] for call in service.ingest_bars.await_args_list]
    assert synced_symbols == ["AAPL", "MSFT"]
    assert "seeded/test skipped: 3" in result
    session.commit.assert_called_once()
