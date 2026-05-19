"""Tests for options chain service."""
import pytest
from unittest.mock import AsyncMock
from decimal import Decimal

from app.clients.broker.ibkr_adapter import IBKRAdapter
from app.services.option_chain_service import OptionChainService


class TestOptionChainService:
    """Tests for OptionChainService."""

    @pytest.fixture
    def mock_adapter(self):
        return AsyncMock(spec=IBKRAdapter)

    @pytest.fixture
    def service(self, mock_adapter):
        return OptionChainService(mock_adapter)

    @pytest.mark.asyncio
    async def test_get_available_expirations(self, service, mock_adapter):
        """Test getting available expiration dates."""
        expected_expirations = ["20260117", "20260121", "20260215", "20260219", "20260321"]
        mock_adapter.get_option_months = AsyncMock(return_value=expected_expirations)
        
        expirations = await service.get_available_expirations(265598)
        
        assert len(expirations) == 5
        assert "20260117" in expirations
        mock_adapter.get_option_months.assert_called_once_with(265598)

    @pytest.mark.asyncio
    async def test_get_strikes(self, service, mock_adapter):
        """Test getting available strikes."""
        expected_strikes = [170, 172.5, 175, 177.5, 180, 182.5, 185]
        mock_adapter.get_option_strikes = AsyncMock(return_value=expected_strikes)
        
        strikes = await service.get_strikes(265598, "20260117")
        
        assert len(strikes) == 7
        assert strikes[0] == Decimal("170")
        assert strikes[-1] == Decimal("185")
        mock_adapter.get_option_strikes.assert_called_once_with(
            265598, expiration="20260117"
        )

    @pytest.mark.asyncio
    async def test_get_option_contracts_calls(self, service, mock_adapter):
        """Test getting call option contracts."""
        expected_contracts = [
            {"conid": 123456, "strike": 175, "right": "CALL", "expiration": "20260117"},
            {"conid": 123457, "strike": 180, "right": "CALL", "expiration": "20260117"},
        ]
        mock_adapter.get_option_contracts = AsyncMock(return_value=expected_contracts)
        
        contracts = await service.get_option_contracts(265598, "20260117", right="CALL")
        
        assert len(contracts) == 2
        assert contracts[0]["right"] == "CALL"
        mock_adapter.get_option_contracts.assert_called_once_with(
            265598, expiration="20260117", right="CALL"
        )

    @pytest.mark.asyncio
    async def test_get_option_contracts_puts(self, service, mock_adapter):
        """Test getting put option contracts."""
        expected_contracts = [
            {"conid": 223456, "strike": 170, "right": "PUT", "expiration": "20260117"},
            {"conid": 223457, "strike": 165, "right": "PUT", "expiration": "20260117"},
        ]
        mock_adapter.get_option_contracts = AsyncMock(return_value=expected_contracts)
        
        contracts = await service.get_option_contracts(265598, "20260117", right="PUT")
        
        assert len(contracts) == 2
        assert contracts[0]["right"] == "PUT"

    @pytest.mark.asyncio
    async def test_build_call_spread(self, service):
        """Test building a call spread."""
        strategy = await service.build_call_spread(
            conid=265598,
            expiration="20260117",
            long_strike=Decimal("175"),
            short_strike=Decimal("180"),
            quantity=100.0,
        )
        
        assert strategy.name == "CALL_SPREAD"
        assert len(strategy.legs) == 2
        
        long_leg = strategy.legs[0]
        assert long_leg.right == "CALL"
        assert long_leg.strike == Decimal("175")
        assert long_leg.side == "BUY"
        assert long_leg.quantity == 100.0
        
        short_leg = strategy.legs[1]
        assert short_leg.right == "CALL"
        assert short_leg.strike == Decimal("180")
        assert short_leg.side == "SELL"

    @pytest.mark.asyncio
    async def test_build_put_spread(self, service):
        """Test building a put spread."""
        strategy = await service.build_put_spread(
            conid=265598,
            expiration="20260117",
            long_strike=Decimal("170"),
            short_strike=Decimal("165"),
            quantity=100.0,
        )
        
        assert strategy.name == "PUT_SPREAD"
        assert len(strategy.legs) == 2
        
        long_leg = strategy.legs[0]
        assert long_leg.right == "PUT"
        assert long_leg.strike == Decimal("170")
        assert long_leg.side == "BUY"
        
        short_leg = strategy.legs[1]
        assert short_leg.right == "PUT"
        assert short_leg.strike == Decimal("165")
        assert short_leg.side == "SELL"

    @pytest.mark.asyncio
    async def test_build_collar(self, service):
        """Test building a collar strategy."""
        strategy = await service.build_collar(
            conid=265598,
            expiration="20260117",
            call_strike=Decimal("185"),
            put_strike=Decimal("165"),
            shares=1000.0,  # 10 option contracts
        )
        
        assert strategy.name == "COLLAR"
        assert len(strategy.legs) == 2
        
        put_leg = strategy.legs[0]
        assert put_leg.right == "PUT"
        assert put_leg.strike == Decimal("165")
        assert put_leg.side == "BUY"
        assert put_leg.quantity == 10.0  # 1000 shares / 100
        
        call_leg = strategy.legs[1]
        assert call_leg.right == "CALL"
        assert call_leg.strike == Decimal("185")
        assert call_leg.side == "SELL"
        assert call_leg.quantity == 10.0
