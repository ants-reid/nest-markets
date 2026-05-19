"""Tests for contract resolution and advanced order services."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.clients.broker.ibkr_adapter import IBKRAdapter
from app.clients.broker.broker_interface import OrderResult
from app.config import get_settings
from app.services.broker_mode_guard import LiveExecutionBlockedError
from app.services.trading_control_service import TradingControlMisconfiguredError
from app.services.contract_resolution_service import ContractResolutionService
from app.services.advanced_order_service import (
    AdvancedOrderService,
    BracketOrderConfig,
    AlgoOrderConfig,
)

# After the trading-control gate was hardened, an inconsistent env
# combination (e.g. LIVE_EXECUTION_ENABLED=true with BROKER_MODE=paper)
# now correctly trips TradingControlMisconfiguredError BEFORE the
# live-blocked check has a chance to run. Both errors are safety-blocking;
# the guarantee these tests assert is that the order is REFUSED. We
# therefore accept either error class.
_LIVE_BLOCKED_OR_MISCONFIGURED = (LiveExecutionBlockedError, TradingControlMisconfiguredError)


class TestContractResolutionService:
    """Tests for ContractResolutionService."""

    @pytest.fixture
    def mock_adapter(self):
        return AsyncMock(spec=IBKRAdapter)

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_adapter, mock_db):
        return ContractResolutionService(mock_adapter, mock_db)

    @pytest.mark.asyncio
    async def test_resolve_symbol_from_adapter(self, service, mock_adapter):
        """Test resolving symbol directly from adapter (no cache)."""
        mock_adapter.resolve_conid = AsyncMock(return_value=265598)
        
        conid = await service.resolve_symbol("AAPL", cache=False)
        
        assert conid == 265598
        mock_adapter.resolve_conid.assert_called_once_with("AAPL", sec_type="STK")

    @pytest.mark.asyncio
    async def test_resolve_symbol_cache_miss_then_save(self, service, mock_adapter, mock_db):
        """Test cache miss, adapter hit, and DB save."""
        mock_adapter.resolve_conid = AsyncMock(return_value=265598)
        
        # First call (cache check) returns asset with no conid
        mock_asset = MagicMock()
        mock_asset.ibkr_con_id = None
        
        # Set up the mock to return the same asset for both queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_asset
        
        conid = await service.resolve_symbol("AAPL", cache=True)
        
        assert conid == 265598
        assert mock_asset.ibkr_con_id == 265598
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_symbol_cache_hit(self, service, mock_adapter, mock_db):
        """Test cache hit (no adapter call)."""
        mock_asset = MagicMock()
        mock_asset.ibkr_con_id = 265598
        mock_db.query.return_value.filter.return_value.first.return_value = mock_asset
        
        conid = await service.resolve_symbol("AAPL", cache=True)
        
        assert conid == 265598
        # Adapter should not be called
        mock_adapter.resolve_conid.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_fx_pair(self, service, mock_adapter, mock_db):
        """Test resolving FX pair."""
        mock_adapter.resolve_conid = AsyncMock(return_value=12087792)
        mock_asset = MagicMock()
        mock_asset.ibkr_con_id = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_asset
        
        conid = await service.resolve_fx_pair("EUR", "USD")
        
        assert conid == 12087792
        mock_adapter.resolve_conid.assert_called_once_with("EUR.USD", sec_type="CASH")

    @pytest.mark.asyncio
    async def test_resolve_fx_pair_not_found(self, service, mock_adapter, mock_db):
        """Test FX pair not found."""
        mock_adapter.resolve_conid = AsyncMock(
            side_effect=ValueError("No contract found")
        )
        mock_asset = MagicMock()
        mock_asset.ibkr_con_id = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_asset
        
        conid = await service.resolve_fx_pair("XYZ", "USD")
        
        assert conid is None


class TestAdvancedOrderService:
    """Tests for AdvancedOrderService."""

    @pytest.fixture
    def mock_adapter(self):
        return AsyncMock(spec=IBKRAdapter)

    @pytest.fixture
    def service(self, mock_adapter):
        return AdvancedOrderService(mock_adapter)

    @pytest.mark.asyncio
    async def test_submit_bracket_order(self, service, mock_adapter):
        """Test bracket order submission."""
        expected_results = [
            OrderResult(broker_order_id="111", status="SUBMITTED"),
            OrderResult(broker_order_id="112", status="SUBMITTED"),
            OrderResult(broker_order_id="113", status="SUBMITTED"),
        ]
        mock_adapter.submit_bracket_order = AsyncMock(return_value=expected_results)
        
        config = BracketOrderConfig(
            conid=265598,
            side="BUY",
            quantity=100.0,
            entry_price=175.00,
            take_profit_price=180.00,
            stop_loss_price=170.00,
        )
        
        results = await service.submit_bracket_order(config)
        
        assert len(results) == 3
        assert results[0].broker_order_id == "111"
        mock_adapter.submit_bracket_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_oca_order(self, service, mock_adapter):
        """Test OCA order submission."""
        expected_results = [
            OrderResult(broker_order_id="201", status="SUBMITTED"),
            OrderResult(broker_order_id="202", status="SUBMITTED"),
        ]
        mock_adapter.submit_oca_order = AsyncMock(return_value=expected_results)
        
        legs = [
            {"conid": 265598, "orderType": "LMT", "side": "BUY", "quantity": 100, "price": 175},
            {"conid": 265598, "orderType": "LMT", "side": "SELL", "quantity": 100, "price": 180},
        ]
        
        results = await service.submit_oca_order(legs)
        
        assert len(results) == 2
        mock_adapter.submit_oca_order.assert_called_once_with(legs)

    @pytest.mark.asyncio
    async def test_submit_algo_order_adaptive(self, service, mock_adapter):
        """Test adaptive algo order submission."""
        expected_result = OrderResult(
            broker_order_id="301",
            status="SUBMITTED",
        )
        mock_adapter.submit_order = AsyncMock(return_value=expected_result)
        
        config = AlgoOrderConfig(
            conid=265598,
            side="BUY",
            quantity=100.0,
            algo_type="Adaptive",
            price=175.00,
        )
        
        result = await service.submit_algo_order(config)
        
        assert result.broker_order_id == "301"
        mock_adapter.submit_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_algo_order_vwap(self, service, mock_adapter):
        """Test VWAP algo order submission."""
        expected_result = OrderResult(
            broker_order_id="302",
            status="SUBMITTED",
        )
        mock_adapter.submit_order = AsyncMock(return_value=expected_result)
        
        config = AlgoOrderConfig(
            conid=265598,
            side="BUY",
            quantity=100.0,
            algo_type="Vwap",
            price=175.00,
            max_pct_vol=0.1,
        )
        
        result = await service.submit_algo_order(config)
        
        assert result.broker_order_id == "302"


# ---------------------------------------------------------------------------
# MH-26 Operational Verification — AdvancedOrderService guard trips
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestAdvancedOrderServiceGuard:
    """assert_paper_mode() must trip for all three submission methods when live config is set."""

    @pytest.fixture
    def mock_adapter(self):
        return AsyncMock(spec=IBKRAdapter)

    @pytest.fixture
    def service(self, mock_adapter):
        return AdvancedOrderService(mock_adapter)

    @pytest.mark.asyncio
    async def test_bracket_order_blocked_when_live_execution_enabled(self, service, monkeypatch):
        """submit_bracket_order must raise LiveExecutionBlockedError when LIVE_EXECUTION_ENABLED=true."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        get_settings.cache_clear()
        config = BracketOrderConfig(
            conid=265598, side="BUY", quantity=10.0,
            entry_price=175.0, take_profit_price=180.0, stop_loss_price=170.0,
        )
        with pytest.raises(_LIVE_BLOCKED_OR_MISCONFIGURED):
            await service.submit_bracket_order(config)

    @pytest.mark.asyncio
    async def test_oca_order_blocked_when_broker_mode_live(self, service, monkeypatch):
        """submit_oca_order must refuse the order when BROKER_MODE=live."""
        monkeypatch.setenv("BROKER_MODE", "live")
        get_settings.cache_clear()
        with pytest.raises(_LIVE_BLOCKED_OR_MISCONFIGURED):
            await service.submit_oca_order([
                {"conid": 265598, "orderType": "LMT", "side": "BUY", "quantity": 10, "price": 175},
            ])

    @pytest.mark.asyncio
    async def test_algo_order_blocked_when_ibkr_account_type_live(self, service, monkeypatch):
        """submit_algo_order must refuse the order when IBKR_ACCOUNT_TYPE=live."""
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        config = AlgoOrderConfig(
            conid=265598, side="BUY", quantity=10.0,
            algo_type="Adaptive", price=175.0,
        )
        with pytest.raises(_LIVE_BLOCKED_OR_MISCONFIGURED):
            await service.submit_algo_order(config)

    @pytest.mark.asyncio
    async def test_bracket_order_allowed_in_paper_mode(self, service, mock_adapter):
        """submit_bracket_order must succeed (reach adapter) when env is safe paper mode."""
        expected = [OrderResult(broker_order_id="111", status="SUBMITTED")]
        mock_adapter.submit_bracket_order = AsyncMock(return_value=expected)
        config = BracketOrderConfig(
            conid=265598, side="BUY", quantity=10.0,
            entry_price=175.0, take_profit_price=180.0, stop_loss_price=170.0,
        )
        results = await service.submit_bracket_order(config)
        assert len(results) == 1
        mock_adapter.submit_bracket_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_oca_order_allowed_in_paper_mode(self, service, mock_adapter):
        """submit_oca_order must succeed (reach adapter) when env is safe paper mode."""
        expected = [OrderResult(broker_order_id="201", status="SUBMITTED")]
        mock_adapter.submit_oca_order = AsyncMock(return_value=expected)
        legs = [{"conid": 265598, "orderType": "LMT", "side": "BUY", "quantity": 10, "price": 175}]
        results = await service.submit_oca_order(legs)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_algo_order_allowed_in_paper_mode(self, service, mock_adapter):
        """submit_algo_order must succeed (reach adapter) when env is safe paper mode."""
        expected = OrderResult(broker_order_id="301", status="SUBMITTED")
        mock_adapter.submit_order = AsyncMock(return_value=expected)
        config = AlgoOrderConfig(
            conid=265598, side="BUY", quantity=10.0,
            algo_type="Adaptive", price=175.0,
        )
        result = await service.submit_algo_order(config)
        assert result.broker_order_id == "301"
