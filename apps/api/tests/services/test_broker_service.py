"""Tests for BrokerGatewayFactory and BrokerService."""
from datetime import datetime, timezone, date as _date_today_for_test
import pytest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.broker.broker_interface import (
    AccountInfo,
    OrderRequest,
    OrderResult,
    PositionInfo,
)
from app.clients.broker.gateway_factory import BrokerGatewayFactory
from app.clients.broker.ibkr_adapter import IBKRAdapter
from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.session import SessionLocal
from app.services.broker_service import BrokerService, PaperPreflightBlockedError
from app.services.trading_control_service import AutoTradingBlockedError, LiveTradingNotArmedError


class TestBrokerGatewayFactory:
    """Tests for BrokerGatewayFactory."""

    def test_create_ibkr_default_url(self):
        """Test creating IBKR adapter with default paper gateway URL."""
        factory = BrokerGatewayFactory()
        adapter = factory.create("ibkr")
        
        assert isinstance(adapter, IBKRAdapter)
        assert adapter._base_url == "https://localhost:5000/v1/api"

    def test_create_ibkr_custom_url(self):
        """Test creating IBKR adapter with custom URL."""
        factory = BrokerGatewayFactory()
        adapter = factory.create(
            "ibkr",
            base_url="https://api.ibkr.com/v1/api",
        )
        
        assert isinstance(adapter, IBKRAdapter)
        assert adapter._base_url == "https://api.ibkr.com/v1/api"

    def test_create_ibkr_custom_timeout(self):
        """Test creating IBKR adapter with custom timeout."""
        factory = BrokerGatewayFactory()
        adapter = factory.create("ibkr", timeout=15.0)
        
        assert adapter._timeout == 15.0

    def test_create_paper_not_implemented(self):
        """Test that paper trading adapter is not yet implemented."""
        factory = BrokerGatewayFactory()
        with pytest.raises(NotImplementedError):
            factory.create("paper")

    def test_create_unknown_broker_type(self):
        """Test error on unknown broker type."""
        factory = BrokerGatewayFactory()
        with pytest.raises(ValueError, match="Unknown broker type"):
            factory.create("unknown_broker")


class TestBrokerService:
    """Tests for BrokerService."""

    @pytest.fixture
    def mock_broker(self):
        """Create a mock broker adapter."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_broker):
        """Create a BrokerService with a mocked adapter."""
        return BrokerService(broker=mock_broker)

    @pytest.fixture(autouse=True)
    def clean_broker_submit_decisions(self):
        with SessionLocal() as session:
            session.query(BrokerSubmitDecision).delete(synchronize_session=False)
            session.commit()
        yield
        with SessionLocal() as session:
            session.query(BrokerSubmitDecision).delete(synchronize_session=False)
            session.commit()

    @pytest.mark.asyncio
    async def test_init_with_broker(self, mock_broker):
        """Test service initialization with provided broker."""
        service = BrokerService(broker=mock_broker)
        assert service._broker is mock_broker

    @pytest.mark.asyncio
    async def test_init_without_broker(self):
        """Test service initialization without broker (lazy loading)."""
        service = BrokerService()
        assert service._broker is None

    def test_preflight_decision_builder_delegates_to_split_helper(self, service):
        expected = {
            "decision_status": "allowed",
            "submit_gate": "not_applied",
            "advisory_count": 0,
            "would_block_count": 0,
            "blocking_count": 0,
            "advisory_items": [],
            "would_block_items": [],
            "blocking_items": [],
        }
        with patch.object(
            service._preflight_decisions,
            "build_preflight_decision",
            return_value=expected,
        ) as mocked:
            result = service._build_preflight_decision(issues=[], warnings=[])

        assert result == expected
        mocked.assert_called_once_with(issues=[], warnings=[])

    def test_preflight_warning_collection_delegates_to_split_helper(self, service):
        request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="MARKET",
        )
        expected = ([{"code": "advisory", "message": "ok"}], {"daily_pnl": 0.0})
        with patch.object(
            service._preflight_advisory,
            "collect_preflight_warnings",
            return_value=expected,
        ) as mocked:
            result = service._collect_preflight_warnings(request, None, None)

        assert result == expected
        mocked.assert_called_once_with(request, None, None)

    @pytest.mark.asyncio
    async def test_get_account_info_fresh(self, service, mock_broker):
        """Test fetching fresh account info (no cache)."""
        expected_info = AccountInfo(
            net_liquidation=Decimal("100000"),
            cash_balance=Decimal("50000"),
            buying_power=Decimal("100000"),
        )
        mock_broker.get_account_info = AsyncMock(return_value=expected_info)
        
        info = await service.get_account_info(use_cache=False)
        
        assert info == expected_info
        assert service._cached_account_info == expected_info

    @pytest.mark.asyncio
    async def test_get_account_info_cached(self, service, mock_broker):
        """Test returning cached account info."""
        cached_info = AccountInfo(
            net_liquidation=Decimal("100000"),
            cash_balance=Decimal("50000"),
            buying_power=Decimal("100000"),
        )
        service._cached_account_info = cached_info
        
        info = await service.get_account_info(use_cache=True)
        
        assert info == cached_info
        # Should not call broker when using cache
        mock_broker.get_account_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_positions(self, service, mock_broker):
        """Test fetching positions from broker."""
        positions = [
            PositionInfo(
                conid=265598,
                ticker="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                avg_cost=Decimal("150.00"),
            ),
            PositionInfo(
                conid=272093,
                ticker="MSFT",
                side="BUY",
                quantity=Decimal("50"),
                avg_cost=Decimal("300.00"),
            ),
        ]
        mock_broker.get_positions = AsyncMock(return_value=positions)
        
        result = await service.get_positions()
        
        assert len(result) == 2
        assert result[0].ticker == "AAPL"
        assert result[1].ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_submit_order_success(self, service, mock_broker):
        """Test successful order submission."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            order_type="MARKET",
        )
        expected_result = OrderResult(
            broker_order_id="123456",
            status="SUBMITTED",
        )
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])
        mock_broker.submit_order = AsyncMock(return_value=expected_result)

        with patch.object(service, "get_daily_pnl", return_value={"daily_pnl": 0.0, "daily_loss": 0.0}), patch.object(
            service,
            "_collect_preflight_warnings",
            return_value=([], {}),
        ):
            result = await service.submit_order(order_request)

        assert result == expected_result
        mock_broker.submit_order.assert_called_once_with(order_request)

    @pytest.mark.asyncio
    async def test_submit_order_blocks_when_paper_preflight_would_block(self, service, mock_broker):
        """Paper submit must reject would-block preflight findings before broker execution."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            order_type="LIMIT",
            limit_price=Decimal("180.5"),
        )

        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])

        with patch.object(service, "get_daily_pnl", return_value={"daily_pnl": 0.0, "daily_loss": 0.0}), patch.object(
            service,
            "_collect_preflight_warnings",
            return_value=(
                [
                    {
                        "code": "emergency_stop_active",
                        "message": "Trading halt is active and will block paper submit.",
                        "severity": "warning",
                        "source": "trading_halt",
                        "enforcement_enabled": False,
                    }
                ],
                {},
            ),
        ):
            with pytest.raises(PaperPreflightBlockedError) as exc_info:
                await service.submit_order(order_request)

        assert exc_info.value.preflight_decision["submit_gate"] == "blocked"
        assert exc_info.value.preflight_decision["decision_status"] == "blocked"
        assert exc_info.value.blocking_reasons[0]["code"] == "emergency_stop_active"
        mock_broker.submit_order.assert_not_called()

        with SessionLocal() as session:
            rows = (
                session.query(BrokerSubmitDecision)
                .order_by(BrokerSubmitDecision.created_at.asc())
                .all()
            )
            assert len(rows) == 2
            assert rows[0].preflight_json["source"] == "submit_preflight"
            assert rows[0].would_block is True
            assert rows[0].preflight_json["allowed_to_submit"] is False
            assert rows[1].preflight_json["source"] == "submit_attempt"
            assert rows[1].would_block is True
            assert rows[1].preflight_json["submit_gate"] == "blocked"

    @pytest.mark.asyncio
    async def test_submit_order_persists_allowed_submit_attempt(self, service, mock_broker):
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("5"),
            order_type="MARKET",
        )
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])
        mock_broker.submit_order = AsyncMock(
            return_value=OrderResult(broker_order_id="abc-123", status="SUBMITTED")
        )

        with patch.object(service, "get_daily_pnl", return_value={"daily_pnl": 0.0, "daily_loss": 0.0}), patch.object(
            service,
            "_collect_preflight_warnings",
            return_value=([], {}),
        ):
            await service.submit_order(order_request)

        with SessionLocal() as session:
            rows = (
                session.query(BrokerSubmitDecision)
                .order_by(BrokerSubmitDecision.created_at.asc())
                .all()
            )
            assert len(rows) == 2
            preflight_row = rows[0]
            submit_row = rows[1]
            assert preflight_row.preflight_json["source"] == "submit_preflight"
            assert preflight_row.preflight_json["decision_status"] == "allowed"
            assert submit_row.preflight_json["source"] == "submit_attempt"
            assert submit_row.preflight_json["decision_status"] == "allowed"
            assert submit_row.preflight_json["allowed_to_submit"] is True
            assert submit_row.preflight_json["submit_gate"] == "allowed"
            assert submit_row.preflight_json["broker_order_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_submit_order_fails_closed_when_preflight_errors(self, service, mock_broker):
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            order_type="LIMIT",
            limit_price=Decimal("180.5"),
        )
        mock_broker.get_account_info = AsyncMock(side_effect=RuntimeError("snapshot unavailable"))

        with pytest.raises(PaperPreflightBlockedError) as exc_info:
            await service.submit_order(order_request)

        assert exc_info.value.preflight_decision["decision_status"] == "error"
        assert exc_info.value.preflight_decision["submit_gate"] == "blocked"
        assert exc_info.value.blocking_reasons[0]["code"] == "preflight_evaluation_error"
        mock_broker.submit_order.assert_not_called()

        with SessionLocal() as session:
            rows = (
                session.query(BrokerSubmitDecision)
                .order_by(BrokerSubmitDecision.created_at.asc())
                .all()
            )
            assert len(rows) == 2
            assert rows[0].preflight_json["source"] == "submit_preflight"
            assert rows[1].preflight_json["source"] == "submit_attempt"
            assert rows[0].preflight_json["decision_status"] == "error"
            assert rows[1].preflight_json["allowed_to_submit"] is False

    @pytest.mark.asyncio
    async def test_dry_run_persists_sanitized_decision_payload(self, service):
        long_message = "x" * 800
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            order_type="LIMIT",
            limit_price=Decimal("180.5"),
        )
        with patch.object(
            service,
            "_collect_preflight_warnings",
            return_value=(
                [
                    {
                        "code": "emergency_stop_active",
                        "message": long_message,
                        "severity": "warning",
                        "source": "trading_halt",
                        "enforcement_enabled": True,
                    }
                ],
                {
                    "cash_balance": 99999.0,
                    "buying_power": 123456.0,
                },
            ),
        ):
            service.dry_run_order(
                order_request,
                persist_decision=True,
                decision_source="dry_run",
                intent="manual",
            )

        with SessionLocal() as session:
            row = session.query(BrokerSubmitDecision).one()
            payload = row.preflight_json
            assert payload["source"] == "dry_run"
            assert payload["decision_status"] == "blocked"
            assert payload["allowed_to_submit"] is False
            assert len(row.blocked_reason_text or "") <= 500
            assert "cash_balance" not in payload
            assert "buying_power" not in payload

    @pytest.mark.asyncio
    async def test_submit_order_zero_quantity(self, service):
        """Test order submission with invalid quantity."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("0"),
            order_type="MARKET",
        )
        
        with pytest.raises(ValueError, match="Quantity must be > 0"):
            await service.submit_order(order_request)

    @pytest.mark.asyncio
    async def test_submit_order_invalid_side(self, service):
        """Test order submission with invalid side."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="INVALID",
            quantity=Decimal("100"),
            order_type="MARKET",
        )
        
        with pytest.raises(ValueError, match="Invalid side"):
            await service.submit_order(order_request)

    @pytest.mark.asyncio
    async def test_submit_order_rejected(self, service, mock_broker):
        """Test handling of rejected order."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("10000"),
            order_type="MARKET",
        )
        rejected_result = OrderResult(
            broker_order_id="",
            status="REJECTED",
            error_message="Insufficient buying power",
        )
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])
        mock_broker.submit_order = AsyncMock(return_value=rejected_result)

        with patch.object(service, "get_daily_pnl", return_value={"daily_pnl": 0.0, "daily_loss": 0.0}), patch.object(
            service,
            "_collect_preflight_warnings",
            return_value=([], {}),
        ):
            result = await service.submit_order(order_request)
        
        assert result.status == "REJECTED"
        assert "buying power" in result.error_message

    @pytest.mark.asyncio
    async def test_submit_order_mode_guard_block_persists_attempt(self, service, mock_broker):
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="MARKET",
        )

        with patch(
            "app.services.broker_service.assert_order_submission_allowed",
            side_effect=LiveTradingNotArmedError("live submit disabled"),
        ):
            with pytest.raises(LiveTradingNotArmedError):
                await service.submit_order(order_request)

        mock_broker.submit_order.assert_not_called()
        with SessionLocal() as session:
            row = session.query(BrokerSubmitDecision).one()
            assert row.would_block is True
            assert row.preflight_json["source"] == "submit_attempt"
            assert row.preflight_json["decision_status"] == "error"
            assert row.preflight_json["allowed_to_submit"] is False
            assert row.blocked_reason_code == "mode_guard_blocked"

    @pytest.mark.asyncio
    async def test_submit_auto_order_remains_blocked_by_default(self, service, mock_broker):
        """The first auto broker-submit seam must remain blocked by default."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            order_type="LIMIT",
            limit_price=Decimal("180.5"),
        )

        with pytest.raises(AutoTradingBlockedError):
            await service.submit_auto_order(order_request)

        mock_broker.submit_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_auto_order_allowed_only_for_controlled_scheduled_auto_paper(
        self,
        service,
        mock_broker,
        monkeypatch,
    ):
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("1"),
            order_type="LIMIT",
            limit_price=Decimal("50"),
        )
        expected_result = OrderResult(
            broker_order_id="AUTO-OK-1",
            status="SUBMITTED",
        )
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])
        mock_broker.submit_order = AsyncMock(return_value=expected_result)

        controlled_env = {
            "AUTO_PAPER_ENABLED": "true",
            "AUTO_PAPER_MAX_ORDERS_PER_RUN": "3",
            "AUTO_PAPER_MAX_ORDERS_PER_DAY": "25",
            "AUTO_PAPER_MAX_NOTIONAL_USD": "1000",
            "AUTO_PAPER_SYMBOL_ALLOWLIST": "AAPL",
            "AUTO_PAPER_ORDER_TYPE": "LIMIT",
            "AUTO_PAPER_LIMIT_PRICE": "50.00",
            "AUTO_PAPER_REQUIRE_TWS": "true",
            "BROKER_PROVIDER": "tws",
            "TWS_ENABLED": "true",
            "BROKER_MODE": "paper",
            "LIVE_EXECUTION_ENABLED": "false",
            "PAPER_TRADING_ENABLED": "true",
            "IBKR_ACCOUNT_TYPE": "paper",
        }
        for key, value in controlled_env.items():
            monkeypatch.setenv(key, value)

        from app.config import get_settings

        get_settings.cache_clear()

        with patch("app.services.trading_control_service._is_scheduled_worker_stack", return_value=True), patch.object(
            service,
            "get_daily_pnl",
            return_value={"daily_pnl": 0.0, "daily_loss": 0.0},
        ), patch.object(
            service,
            "_collect_preflight_warnings",
            return_value=([], {}),
        ):
            result = await service.submit_auto_order(order_request)

        assert result == expected_result
        mock_broker.submit_order.assert_called_once_with(order_request)

    @pytest.mark.asyncio
    async def test_dry_run_order_ready_does_not_submit(self, service, mock_broker):
        """Dry-run should validate a good request and never submit to broker."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            order_type="LIMIT",
            limit_price=Decimal("180.5"),
        )

        result = service.dry_run_order(order_request)

        assert result["status"] == "ready"
        assert result["mode_guard_ok"] is True
        assert result["request_valid"] is True
        assert result["estimated_notional"] == 1805.0
        assert result["issues"] == []
        mock_broker.submit_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_order_invalid_quantity(self, service):
        """Dry-run should surface validation issues for bad requests."""
        order_request = OrderRequest(
            ticker="AAPL",
            side="BUY",
            quantity=Decimal("0"),
            order_type="MARKET",
        )

        result = service.dry_run_order(order_request)

        assert result["status"] == "invalid"
        assert result["mode_guard_ok"] is True
        assert result["request_valid"] is False
        assert any(issue["code"] == "invalid_quantity" for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, service, mock_broker):
        """Test successful order cancellation."""
        mock_broker.cancel_order = AsyncMock(return_value=True)
        
        success = await service.cancel_order("123456")
        
        assert success is True

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, service, mock_broker):
        """Test order cancellation failure."""
        mock_broker.cancel_order = AsyncMock(return_value=False)
        
        success = await service.cancel_order("999999")
        
        assert success is False

    @pytest.mark.asyncio
    async def test_get_order_status(self, service, mock_broker):
        """Test order status polling."""
        status_dict = {
            "order_id": "123456",
            "order_status": "Filled",
            "avgPrice": 175.25,
        }
        mock_broker.get_order_status = AsyncMock(return_value=status_dict)
        
        status = await service.get_order_status("123456")
        
        assert status["order_status"] == "Filled"

    @pytest.mark.asyncio
    async def test_reconcile_positions_perfect_match(self, service, mock_broker):
        """Test position reconciliation with perfect match."""
        actual_positions = [
            PositionInfo(
                conid=265598,
                ticker="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                avg_cost=Decimal("150.00"),
            ),
        ]
        mock_broker.get_positions = AsyncMock(return_value=actual_positions)
        
        expected = {"AAPL": Decimal("100")}
        
        report = await service.reconcile_positions(expected)
        
        assert report["matched_count"] == 1
        assert report["mismatch_count"] == 0
        assert len(report["mismatches"]) == 0

    @pytest.mark.asyncio
    async def test_reconcile_positions_mismatch(self, service, mock_broker):
        """Test position reconciliation with mismatches."""
        actual_positions = [
            PositionInfo(
                conid=265598,
                ticker="AAPL",
                side="BUY",
                quantity=Decimal("75"),
                avg_cost=Decimal("150.00"),
            ),
        ]
        mock_broker.get_positions = AsyncMock(return_value=actual_positions)
        
        expected = {"AAPL": Decimal("100")}
        
        report = await service.reconcile_positions(expected)
        
        assert report["mismatch_count"] == 1
        assert "AAPL" in report["mismatches"]
        assert report["mismatches"]["AAPL"]["expected"] == "100"
        assert report["mismatches"]["AAPL"]["actual"] == "75"
        assert report["mismatches"]["AAPL"]["delta"] == "-25"

    @pytest.mark.asyncio
    async def test_reconcile_positions_missing_position(self, service, mock_broker):
        """Test reconciliation when position doesn't exist."""
        actual_positions = []
        mock_broker.get_positions = AsyncMock(return_value=actual_positions)
        
        expected = {"AAPL": Decimal("100")}
        
        report = await service.reconcile_positions(expected)
        
        assert report["mismatch_count"] == 1
        assert "AAPL" in report["mismatches"]
        assert report["mismatches"]["AAPL"]["actual"] == "0"

    @pytest.mark.asyncio
    async def test_capture_daily_pnl_snapshot_manual_records_snapshot(self, service, mock_broker):
        """MH-46A: manual capture writes one pnl_snapshots row from broker data."""
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("105000"),
                cash_balance=Decimal("42000"),
                buying_power=Decimal("80000"),
                currency="USD",
                unrealized_pnl=Decimal("1250"),
            )
        )
        mock_broker.get_positions = AsyncMock(
            return_value=[
                PositionInfo(
                    conid=1,
                    ticker="AAPL",
                    side="BUY",
                    quantity=Decimal("10"),
                    avg_cost=Decimal("180"),
                    market_price=Decimal("185"),
                    market_value=Decimal("1850"),
                    unrealized_pnl=Decimal("50"),
                ),
                PositionInfo(
                    conid=2,
                    ticker="TSLA",
                    side="SELL",
                    quantity=Decimal("5"),
                    avg_cost=Decimal("170"),
                    market_price=Decimal("160"),
                    market_value=Decimal("800"),
                    unrealized_pnl=Decimal("1200"),
                ),
            ]
        )

        mock_row = SimpleNamespace(
            snapshot_ts=SimpleNamespace(isoformat=lambda: "2026-04-28T12:00:00+00:00"),
            equity=105000.0,
            cash=42000.0,
            gross_exposure=2650.0,
            net_exposure=1050.0,
            open_pnl=1250.0,
            closed_pnl=None,
        )

        with patch("app.services.broker_service.SessionLocal") as mock_session_cls, patch(
            "app.services.pnl_service.PnlService"
        ) as mock_pnl_service_cls, patch(
            "app.services.broker_service.get_settings"
        ) as mock_get_settings:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = mock_session
            mock_get_settings.return_value = SimpleNamespace(ibkr_account_id="DU123456")

            mock_pnl_svc = MagicMock()
            mock_pnl_svc.record_snapshot.return_value = mock_row
            mock_pnl_service_cls.return_value = mock_pnl_svc

            result = await service.capture_daily_pnl_snapshot()

        assert result["snapshot_ts"] == "2026-04-28T12:00:00+00:00"
        assert result["equity"] == pytest.approx(105000.0)
        assert result["cash"] == pytest.approx(42000.0)
        assert result["gross_exposure"] == pytest.approx(2650.0)
        assert result["net_exposure"] == pytest.approx(1050.0)
        assert result["open_pnl"] == pytest.approx(1250.0)
        assert result["source"] == "manual"
        assert result["account_id"] == "DU123456"
        assert result["broker_mode"]["mode"] == "paper"
        assert result["position_count"] == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_daily_pnl_snapshot_scheduled_sets_source(self, service, mock_broker):
        """MH-46A: scheduled capture keeps source label and account metadata."""
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])

        mock_row = SimpleNamespace(
            snapshot_ts=SimpleNamespace(isoformat=lambda: "2026-04-28T12:00:00+00:00"),
            equity=100000.0,
            cash=50000.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            open_pnl=0.0,
            closed_pnl=None,
        )

        with patch("app.services.broker_service.SessionLocal") as mock_session_cls, patch(
            "app.services.pnl_service.PnlService"
        ) as mock_pnl_service_cls, patch(
            "app.services.broker_service.get_settings"
        ) as mock_get_settings:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = mock_session
            mock_get_settings.return_value = SimpleNamespace(ibkr_account_id="DU999000")

            mock_pnl_svc = MagicMock()
            mock_pnl_svc.record_snapshot.return_value = mock_row
            mock_pnl_service_cls.return_value = mock_pnl_svc

            result = await service.capture_daily_pnl_snapshot(source="scheduled")

        assert result["source"] == "scheduled"
        assert result["account_id"] == "DU999000"
        assert result["broker_mode"]["mode"] == "paper"

    @pytest.mark.asyncio
    async def test_capture_daily_pnl_snapshot_ingests_closed_pnl_from_fill_events(self, service, mock_broker):
        """MH-46B-2: closed_pnl is populated from realized fill-event fields when present."""
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("101000"),
                cash_balance=Decimal("51000"),
                buying_power=Decimal("101000"),
                unrealized_pnl=Decimal("250"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])
        # _derive_closed_pnl_from_fill_events filters by date.today(); using a
        # hard-coded date causes events to be skipped once that date is past.
        _today_str = _date_today_for_test.today().isoformat()
        mock_broker.get_trades = AsyncMock(
            return_value=[
                {"trade_time": f"{_today_str} 10:10:00", "realizedPnl": "30.5"},
                {"trade_time": f"{_today_str} 11:30:00", "realized_pnl": 19.5},
            ]
        )

        mock_row = SimpleNamespace(
            snapshot_ts=SimpleNamespace(isoformat=lambda: "2026-04-28T12:00:00+00:00"),
            equity=101000.0,
            cash=51000.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            open_pnl=250.0,
            closed_pnl=50.0,
        )

        with patch("app.services.broker_service.SessionLocal") as mock_session_cls, patch(
            "app.services.pnl_service.PnlService"
        ) as mock_pnl_service_cls, patch(
            "app.services.broker_service.get_settings"
        ) as mock_get_settings:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = mock_session
            mock_get_settings.return_value = SimpleNamespace(ibkr_account_id="DU777777")

            mock_pnl_svc = MagicMock()
            mock_pnl_svc.record_snapshot.return_value = mock_row
            mock_pnl_service_cls.return_value = mock_pnl_svc

            result = await service.capture_daily_pnl_snapshot(source="scheduled")

        assert result["closed_pnl"] == pytest.approx(50.0)
        assert result["closed_pnl_source"] == "broker_trade_events"
        mock_broker.submit_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_capture_daily_pnl_snapshot_closed_pnl_null_without_realized_fields(self, service, mock_broker):
        """MH-46B-2: closed_pnl remains null when trade events have no realized values."""
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
                unrealized_pnl=Decimal("0"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])
        mock_broker.get_trades = AsyncMock(
            return_value=[{"trade_time": "2026-04-28 09:00:00", "symbol": "AAPL"}]
        )

        mock_row = SimpleNamespace(
            snapshot_ts=SimpleNamespace(isoformat=lambda: "2026-04-28T12:00:00+00:00"),
            equity=100000.0,
            cash=50000.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            open_pnl=0.0,
            closed_pnl=None,
        )

        with patch("app.services.broker_service.SessionLocal") as mock_session_cls, patch(
            "app.services.pnl_service.PnlService"
        ) as mock_pnl_service_cls, patch(
            "app.services.broker_service.get_settings"
        ) as mock_get_settings:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = mock_session
            mock_get_settings.return_value = SimpleNamespace(ibkr_account_id="DU000001")

            mock_pnl_svc = MagicMock()
            mock_pnl_svc.record_snapshot.return_value = mock_row
            mock_pnl_service_cls.return_value = mock_pnl_svc

            result = await service.capture_daily_pnl_snapshot(source="scheduled")

        assert result["closed_pnl"] is None
        assert result["closed_pnl_source"] is None

    @pytest.mark.asyncio
    async def test_derive_closed_pnl_returns_none_when_broker_lacks_get_trades(self):
        """MH-46B-2 regression guard (cycle 53): when the active broker
        adapter has no ``get_trades`` method at all (e.g. a stub broker, a
        legacy adapter, or a paper-only broker that never tracks fills),
        ``_derive_closed_pnl_from_fill_events`` MUST return ``(None, None)``
        rather than raising. The snapshot pipeline relies on this contract
        to degrade gracefully — closed_pnl is recorded as null and the
        capture flow proceeds.

        Drift here would silently break the daily pnl snapshot for any
        broker that doesn't implement the optional get_trades hook.
        """
        # SimpleNamespace yields no get_trades attribute, unlike AsyncMock
        # which auto-creates one on access.
        broker_without_get_trades = SimpleNamespace()
        service = BrokerService(broker=broker_without_get_trades)

        closed_pnl, source = await service._derive_closed_pnl_from_fill_events()

        assert closed_pnl is None
        assert source is None

    @pytest.mark.asyncio
    async def test_derive_closed_pnl_returns_none_when_get_trades_not_callable(self):
        """MH-46B-2 regression guard (cycle 53): if a broker exposes
        ``get_trades`` as a non-callable attribute (e.g. an accidental
        property or a misconfigured stub), the snapshot must still
        return ``(None, None)`` rather than crash.
        """
        broker = SimpleNamespace(get_trades="not a callable")
        service = BrokerService(broker=broker)

        closed_pnl, source = await service._derive_closed_pnl_from_fill_events()

        assert closed_pnl is None
        assert source is None

    @pytest.mark.asyncio
    async def test_capture_pnl_snapshot_alias_still_manual_and_no_submit(self, service, mock_broker):
        """MH-46A safety: backward alias remains manual and never submits orders."""
        mock_broker.get_account_info = AsyncMock(
            return_value=AccountInfo(
                net_liquidation=Decimal("100000"),
                cash_balance=Decimal("50000"),
                buying_power=Decimal("100000"),
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[])

        mock_row = SimpleNamespace(
            snapshot_ts=SimpleNamespace(isoformat=lambda: "2026-04-28T12:00:00+00:00"),
            equity=100000.0,
            cash=50000.0,
            gross_exposure=0.0,
            net_exposure=0.0,
            open_pnl=0.0,
            closed_pnl=None,
        )

        with patch("app.services.broker_service.SessionLocal") as mock_session_cls, patch(
            "app.services.pnl_service.PnlService"
        ) as mock_pnl_service_cls, patch(
            "app.services.broker_service.get_settings"
        ) as mock_get_settings:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = mock_session
            mock_get_settings.return_value = SimpleNamespace(ibkr_account_id="")

            mock_pnl_svc = MagicMock()
            mock_pnl_svc.record_snapshot.return_value = mock_row
            mock_pnl_service_cls.return_value = mock_pnl_svc

            result = await service.capture_pnl_snapshot()

        assert result["source"] == "manual"
        mock_broker.submit_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_normalize_and_stage_trade_events_writes_ingestion_summary(self, service, mock_broker):
        """MH-47: normalization ingestion stages events without affecting execution paths."""
        mock_broker.get_trades = AsyncMock(
            return_value=[
                {
                    "orderId": "1001",
                    "order_ref": "P-1",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "size": "10",
                    "price": "185.1",
                    "realizedPnl": "5.0",
                    "trade_time": "2026-04-28T12:00:00+00:00",
                }
            ]
        )

        with patch("app.services.broker_service.SessionLocal") as mock_session_cls, patch(
            "app.services.broker_service.BrokerTradeEventService"
        ) as mock_evt_svc_cls, patch(
            "app.services.broker_service.get_settings"
        ) as mock_get_settings:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = mock_session
            mock_get_settings.return_value = SimpleNamespace(ibkr_account_id="DU111111")

            mock_evt_svc = MagicMock()
            mock_evt_svc.ingest_trade_events.return_value = {
                "received": 1,
                "inserted": 1,
                "skipped": 0,
            }
            mock_evt_svc_cls.return_value = mock_evt_svc

            result = await service.normalize_and_stage_trade_events()

        assert result["received"] == 1
        assert result["inserted"] == 1
        assert result["account_id"] == "DU111111"
        assert result["source"] == "broker_account_trades"
        mock_session.commit.assert_called_once()
        mock_broker.submit_order.assert_not_called()

    def test_get_normalized_trade_events_returns_audit_readback(self, service):
        """MH-47B: readback endpoint data is serialized for provenance auditing."""
        fake_row = SimpleNamespace(
            event_fingerprint="fp-1",
            external_trade_id="ext-1",
            broker_order_id="ord-1",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            fill_price=Decimal("185.1"),
            commission=Decimal("1.0"),
            net_amount=Decimal("1850"),
            realized_pnl=Decimal("5.0"),
            trade_ts=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
            source="broker_account_trades",
            account_id="DU111111",
            broker_provider="ibkr",
            created_at=datetime(2026, 4, 28, 12, 0, 1, tzinfo=timezone.utc),
        )

        with patch("app.services.broker_service.SessionLocal") as mock_session_cls, patch(
            "app.services.broker_service.get_settings"
        ) as mock_get_settings:
            mock_session = MagicMock()
            (
                mock_session.query.return_value
                .order_by.return_value
                .limit.return_value
                .all.return_value
            ) = [fake_row]
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session_cls.return_value = mock_session
            mock_get_settings.return_value = SimpleNamespace(ibkr_account_id="DU111111")

            result = service.get_normalized_trade_events(limit=999)

        assert result["returned"] == 1
        assert result["account_id"] == "DU111111"
        assert result["entries"][0]["event_fingerprint"] == "fp-1"
        assert result["entries"][0]["quantity"] == 10.0
        assert result["entries"][0]["trade_ts"] == "2026-04-28T12:00:00+00:00"
        mock_session.query.return_value.order_by.return_value.limit.assert_called_once_with(500)
