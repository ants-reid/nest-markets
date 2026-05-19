"""Tests for IBKR market data service."""
import pytest
from unittest.mock import AsyncMock
from decimal import Decimal

from app.clients.broker.ibkr_adapter import IBKRAdapter
from app.services.ibkr_market_data_service import IBKRMarketDataService


class TestIBKRMarketDataService:
    """Tests for IBKRMarketDataService."""

    @pytest.fixture
    def mock_adapter(self):
        return AsyncMock(spec=IBKRAdapter)

    @pytest.fixture
    def service(self, mock_adapter):
        return IBKRMarketDataService(mock_adapter)

    @pytest.mark.asyncio
    async def test_get_snapshot(self, service, mock_adapter):
        """Test getting market snapshot."""
        expected_snapshot = {
            "conid": 265598,
            "bid": 175.50,
            "ask": 175.52,
            "last": 175.51,
            "volume": 12345678,
        }
        mock_adapter.get_snapshot = AsyncMock(return_value=expected_snapshot)
        
        snapshot = await service.get_snapshot(265598)
        
        assert snapshot["bid"] == 175.50
        assert snapshot["ask"] == 175.52
        mock_adapter.get_snapshot.assert_called_once_with(265598, fields=None)

    @pytest.mark.asyncio
    async def test_get_snapshot_with_fields(self, service, mock_adapter):
        """Test getting snapshot with specific fields."""
        expected_snapshot = {
            "bid": 175.50,
            "ask": 175.52,
        }
        mock_adapter.get_snapshot = AsyncMock(return_value=expected_snapshot)
        
        snapshot = await service.get_snapshot(265598, fields="bid,ask")
        
        assert snapshot["bid"] == 175.50
        mock_adapter.get_snapshot.assert_called_once_with(265598, fields="bid,ask")

    @pytest.mark.asyncio
    async def test_get_bid_ask(self, service, mock_adapter):
        """Test getting bid/ask spread."""
        expected_snapshot = {
            "bid": 175.50,
            "ask": 175.52,
            "bidSize": 500,
            "askSize": 1000,
        }
        mock_adapter.get_snapshot = AsyncMock(return_value=expected_snapshot)
        
        bid_ask = await service.get_bid_ask(265598)
        
        assert bid_ask["bid"] == 175.50
        assert bid_ask["ask"] == 175.52
        assert bid_ask["bid_size"] == 500
        assert bid_ask["ask_size"] == 1000

    @pytest.mark.asyncio
    async def test_get_last_price(self, service, mock_adapter):
        """Test getting last traded price."""
        expected_snapshot = {"last": 175.51}
        mock_adapter.get_snapshot = AsyncMock(return_value=expected_snapshot)
        
        price = await service.get_last_price(265598)
        
        assert price == Decimal("175.51")

    @pytest.mark.asyncio
    async def test_get_last_price_none(self, service, mock_adapter):
        """Test getting last price when not available."""
        expected_snapshot = {"last": None}
        mock_adapter.get_snapshot = AsyncMock(return_value=expected_snapshot)
        
        price = await service.get_last_price(265598)
        
        assert price is None

    @pytest.mark.asyncio
    async def test_get_historical_data_daily(self, service, mock_adapter):
        """Test getting daily historical bars."""
        expected_bars = [
            {"t": 1640000000, "o": 170.00, "h": 180.00, "l": 169.00, "c": 175.00, "v": 100000},
            {"t": 1640100000, "o": 175.00, "h": 178.00, "l": 174.00, "c": 176.00, "v": 120000},
        ]
        mock_adapter.get_history = AsyncMock(return_value=expected_bars)
        
        bars = await service.get_historical_data(265598, period="1mo", bar="1d")
        
        assert len(bars) == 2
        assert bars[0]["c"] == 175.00
        assert bars[1]["c"] == 176.00
        mock_adapter.get_history.assert_called_once_with(
            conid=265598,
            period="1mo",
            bar="1d",
            outside_rth=False,
        )

    @pytest.mark.asyncio
    async def test_get_historical_data_hourly(self, service, mock_adapter):
        """Test getting hourly historical bars."""
        expected_bars = [
            {"t": 1640000000, "o": 175.00, "h": 175.50, "l": 174.50, "c": 175.25, "v": 5000},
            {"t": 1640003600, "o": 175.25, "h": 175.75, "l": 175.00, "c": 175.50, "v": 6000},
        ]
        mock_adapter.get_history = AsyncMock(return_value=expected_bars)
        
        bars = await service.get_historical_data(265598, period="1w", bar="1h", outside_rth=True)
        
        assert len(bars) == 2
        mock_adapter.get_history.assert_called_once_with(
            conid=265598,
            period="1w",
            bar="1h",
            outside_rth=True,
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_snapshot(self, service, mock_adapter):
        """Test unsubscribing from snapshot."""
        mock_adapter.unsubscribe_snapshot = AsyncMock()
        
        await service.unsubscribe_snapshot(265598)
        
        mock_adapter.unsubscribe_snapshot.assert_called_once_with(265598)

    @pytest.mark.asyncio
    async def test_unsubscribe_all_snapshots(self, service, mock_adapter):
        """Test unsubscribing from all snapshots."""
        mock_adapter.unsubscribe_all_snapshots = AsyncMock()
        
        await service.unsubscribe_all_snapshots()
        
        mock_adapter.unsubscribe_all_snapshots.assert_called_once()
