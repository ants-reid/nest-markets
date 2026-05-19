"""Tests for commission tracking, P&L, and Flex reconciliation services."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.clients.broker.ibkr_adapter import IBKRAdapter
from app.services.commission_tracking_service import CommissionTrackingService
from app.services.ibkr_pnl_service import IBKRPnLService
from app.services.flex_reconciliation_service import (
    FlexReconciliationService,
    FlexPosition,
)


# ── CommissionTrackingService ─────────────────────────────────────────────────

class TestCommissionTrackingService:
    """Tests for CommissionTrackingService (BP-15.22)."""

    @pytest.fixture
    def mock_adapter(self):
        return AsyncMock(spec=IBKRAdapter)

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_adapter, mock_db):
        return CommissionTrackingService(mock_adapter, mock_db)

    @pytest.mark.asyncio
    async def test_get_today_executions(self, service, mock_adapter):
        """Test parsing trade executions from adapter."""
        mock_adapter.get_trades = AsyncMock(return_value=[
            {
                "orderId": "1001",
                "order_ref": "P-12345",
                "symbol": "AAPL",
                "side": "BUY",
                "size": 100,
                "price": 175.50,
                "commission": 1.05,
                "net_amount": 17551.05,
                "trade_time": "2026-04-25 10:30:00",
            }
        ])

        executions = await service.get_today_executions()

        assert len(executions) == 1
        assert executions[0].ticker == "AAPL"
        assert executions[0].fill_price == Decimal("175.50")
        assert executions[0].commission == Decimal("1.05")
        assert executions[0].broker_order_id == "P-12345"

    @pytest.mark.asyncio
    async def test_get_today_executions_empty(self, service, mock_adapter):
        """Test handling empty trade list."""
        mock_adapter.get_trades = AsyncMock(return_value=[])

        executions = await service.get_today_executions()

        assert executions == []

    @pytest.mark.asyncio
    async def test_update_order_commission(self, service, mock_adapter, mock_db):
        """Test updating commission on a matched PaperOrder."""
        mock_adapter.get_trades = AsyncMock(return_value=[
            {
                "orderId": "1001",
                "order_ref": "P-12345",
                "symbol": "AAPL",
                "side": "BUY",
                "size": 100,
                "price": 175.50,
                "commission": 1.05,
                "net_amount": 17551.05,
                "trade_time": "2026-04-25 10:30:00",
            }
        ])

        mock_order = MagicMock()
        mock_order.broker_order_id = "P-12345"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_order

        result = await service.update_order_commission("P-12345")

        assert result is mock_order
        assert mock_order.commission == Decimal("1.05")
        assert mock_order.avg_fill_price == Decimal("175.50")
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_order_commission_not_found_in_trades(self, service, mock_adapter, mock_db):
        """Test when broker_order_id not in today's trades."""
        mock_adapter.get_trades = AsyncMock(return_value=[])

        result = await service.update_order_commission("P-NOTEXIST")

        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_all_commissions(self, service, mock_adapter, mock_db):
        """Test bulk commission reconciliation."""
        mock_adapter.get_trades = AsyncMock(return_value=[
            {
                "orderId": "1001",
                "order_ref": "P-001",
                "symbol": "AAPL",
                "side": "BUY",
                "size": 100,
                "price": 175.50,
                "commission": 1.05,
                "net_amount": 17551.05,
                "trade_time": "2026-04-25 10:30:00",
            }
        ])

        mock_order = MagicMock()
        mock_order.broker_order_id = "P-001"
        mock_order.commission = None
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_order]

        result = await service.reconcile_all_commissions()

        assert result["updated"] == 1
        assert result["not_found"] == 0


# ── IBKRPnLService ────────────────────────────────────────────────────────────

class TestIBKRPnLService:
    """Tests for IBKRPnLService (BP-15.32)."""

    @pytest.fixture
    def mock_adapter(self):
        return AsyncMock(spec=IBKRAdapter)

    @pytest.fixture
    def service(self, mock_adapter):
        return IBKRPnLService(mock_adapter)

    @pytest.mark.asyncio
    async def test_get_pnl_success(self, service, mock_adapter):
        """Test fetching P&L for a specific account."""
        mock_adapter.get_pnl = AsyncMock(return_value={
            "upnl": {
                "DU12345.Core": {
                    "dpl": 1250.50,
                    "upl": 3500.75,
                    "nl": 125000.00,
                }
            }
        })

        summary = await service.get_pnl("DU12345")

        assert summary is not None
        assert summary.account_id == "DU12345"
        assert summary.daily_pnl == Decimal("1250.50")
        assert summary.unrealized_pnl == Decimal("3500.75")
        assert summary.net_liquidation == Decimal("125000.00")

    @pytest.mark.asyncio
    async def test_get_pnl_initial_empty_then_populated(self, service, mock_adapter):
        """Test retry when initial response is empty."""
        mock_adapter.get_pnl = AsyncMock(side_effect=[
            {"upnl": {}},  # First call empty (subscription)
            {"upnl": {"DU12345.Core": {"dpl": 500, "upl": 1000, "nl": 100000}}},
        ])

        summary = await service.get_pnl("DU12345")

        assert summary is not None
        assert summary.daily_pnl == Decimal("500")
        assert mock_adapter.get_pnl.call_count == 2

    @pytest.mark.asyncio
    async def test_get_pnl_unavailable_after_retries(self, service, mock_adapter):
        """Test None returned after max retries with empty response."""
        mock_adapter.get_pnl = AsyncMock(return_value={"upnl": {}})

        summary = await service.get_pnl("DU12345")

        assert summary is None
        assert mock_adapter.get_pnl.call_count == IBKRPnLService.MAX_RETRIES

    @pytest.mark.asyncio
    async def test_get_aggregate_pnl(self, service, mock_adapter):
        """Test fetching P&L for all accounts."""
        mock_adapter.get_pnl = AsyncMock(return_value={
            "upnl": {
                "DU12345.Core": {"dpl": 1000, "upl": 2000, "nl": 100000},
                "DU67890.Core": {"dpl": -500, "upl": 500, "nl": 50000},
            }
        })

        result = await service.get_aggregate_pnl()

        assert len(result) == 2
        assert "DU12345" in result
        assert "DU67890" in result
        assert result["DU12345"].daily_pnl == Decimal("1000")
        assert result["DU67890"].daily_pnl == Decimal("-500")


# ── FlexReconciliationService ─────────────────────────────────────────────────

class TestFlexReconciliationService:
    """Tests for FlexReconciliationService (BP-15.42)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        return FlexReconciliationService(mock_db)

    def test_get_credentials_missing(self, service, monkeypatch):
        """Test ValueError when credentials not set."""
        monkeypatch.delenv("FLEX_TOKEN", raising=False)
        monkeypatch.delenv("FLEX_QUERY_ID", raising=False)

        with pytest.raises(ValueError, match="FLEX_TOKEN"):
            service._get_credentials()

    def test_get_credentials_set(self, service, monkeypatch):
        """Test credentials loaded from environment."""
        monkeypatch.setenv("FLEX_TOKEN", "test-token-12345")
        monkeypatch.setenv("FLEX_QUERY_ID", "999999")

        token, query_id = service._get_credentials()

        assert token == "test-token-12345"
        assert query_id == "999999"

    def test_parse_positions_valid_xml(self, service):
        """Test parsing valid OpenPosition XML elements."""
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse>
  <FlexStatements count="1">
    <FlexStatement accountId="DU12345">
      <OpenPositions>
        <OpenPosition accountId="DU12345" symbol="AAPL" conid="265598"
          position="100" costBasisMoney="17500.00" markPrice="175.00"
          fifoPnlUnrealized="0.00" realizedPnl="0.00" currency="USD"/>
        <OpenPosition accountId="DU12345" symbol="TSLA" conid="76792991"
          position="50" costBasisMoney="12500.00" markPrice="250.00"
          fifoPnlUnrealized="0.00" realizedPnl="0.00" currency="USD"/>
      </OpenPositions>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

        positions = service._parse_positions(xml_text)

        assert len(positions) == 2
        assert positions[0].symbol == "AAPL"
        assert positions[0].conid == 265598
        assert positions[0].quantity == Decimal("100")
        assert positions[1].symbol == "TSLA"

    def test_parse_positions_empty_xml(self, service):
        """Test parsing XML with no positions."""
        xml_text = """<?xml version="1.0"?>
<FlexQueryResponse><FlexStatements count="0"></FlexStatements></FlexQueryResponse>"""

        positions = service._parse_positions(xml_text)

        assert positions == []

    @pytest.mark.asyncio
    async def test_reconcile_perfect_match(self, service, mock_db):
        """Test reconciliation with all positions matching."""
        mock_db_pos = MagicMock()
        mock_db_pos.qty = 100
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            (mock_db_pos, "AAPL")
        ]

        service.fetch_activity_statement = AsyncMock(return_value=[
            FlexPosition(
                account_id="DU12345", symbol="AAPL", conid=265598,
                quantity=Decimal("100"), cost_basis=Decimal("17500"),
                market_value=Decimal("175"), unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
            )
        ])

        report = await service.reconcile()

        assert report.matched == 1
        assert report.missing_in_db == []
        assert report.missing_in_ibkr == []
        assert report.quantity_mismatches == {}

    @pytest.mark.asyncio
    async def test_reconcile_missing_in_db(self, service, mock_db):
        """Test when IBKR has positions not in DB."""
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []

        service.fetch_activity_statement = AsyncMock(return_value=[
            FlexPosition(
                account_id="DU12345", symbol="NVDA", conid=4815747,
                quantity=Decimal("50"), cost_basis=Decimal("30000"),
                market_value=Decimal("600"), unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
            )
        ])

        report = await service.reconcile()

        assert report.matched == 0
        assert "NVDA" in report.missing_in_db

    @pytest.mark.asyncio
    async def test_reconcile_quantity_mismatch(self, service, mock_db):
        """Test quantity mismatch detection."""
        mock_db_pos = MagicMock()
        mock_db_pos.qty = 50  # DB says 50, IBKR says 100
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            (mock_db_pos, "AAPL")
        ]

        service.fetch_activity_statement = AsyncMock(return_value=[
            FlexPosition(
                account_id="DU12345", symbol="AAPL", conid=265598,
                quantity=Decimal("100"), cost_basis=Decimal("17500"),
                market_value=Decimal("175"), unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
            )
        ])

        report = await service.reconcile()

        assert "AAPL" in report.quantity_mismatches
        assert report.quantity_mismatches["AAPL"]["db_quantity"] == "50"
        assert report.quantity_mismatches["AAPL"]["ibkr_quantity"] == "100"
