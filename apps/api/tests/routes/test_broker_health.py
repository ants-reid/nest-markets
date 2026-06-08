"""Operational verification tests for GET /broker/health — MH-27.

Covers:
  - Response shape always matches BrokerHealthSchema
  - status="paper_ready" when guard OK, gateway reachable, account DU-prefixed
  - status="paper_config_only" when guard OK but gateway unreachable
  - status="misconfigured" when any live-mode guard trips
  - account_is_paper True/False based on account ID prefix
  - mode_guard_ok and gateway_reachable fields reflect actual check results
  - is_paper_account_id() — DU prefix, empty, and live account scenarios
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import create_app
from app.config import get_settings
from app.services.broker_mode_guard import is_paper_account_id

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _mock_readiness_dependencies():
    class _StubService:
        def get_runtime_diagnostics(self):
            return {
                "tws_runtime_client_id": 43,
                "tws_connection_state": "connected",
                "tws_last_error_code": None,
                "tws_last_error_message": None,
            }

    with patch(
        "app.api.routes.broker._probe_broker_account_health",
        new=AsyncMock(return_value=(True, True, "IBKR account snapshot loaded.")),
    ), patch(
        "app.api.routes.broker._probe_broker_positions_health",
        new=AsyncMock(return_value=(True, True, "IBKR positions snapshot loaded.")),
    ), patch(
        "app.api.routes.broker.get_auto_paper_status_card",
        return_value={
            "next_run_guidance": {"paper_normal_mode_active": True},
            "candidate_queue": {"eligible_count": 1},
            "audit_alignment": {"status": "ok"},
            "latest_paper_order": None,
        },
    ), patch(
        "app.api.routes.broker.get_broker_service",
        return_value=_StubService(),
    ):
        yield


# ---------------------------------------------------------------------------
# is_paper_account_id unit tests
# ---------------------------------------------------------------------------

class TestIsPaperAccountId:
    """Unit tests for the account-ID paper/live classifier."""

    def test_du_prefix_is_paper(self):
        assert is_paper_account_id("DUP153837") is True

    def test_du_lowercase_is_paper(self):
        assert is_paper_account_id("dup153837") is True

    def test_du_exact_is_paper(self):
        assert is_paper_account_id("DU") is True

    def test_empty_string_treated_as_safe(self):
        """Empty/unconfigured account ID is treated as paper-safe (not yet set)."""
        assert is_paper_account_id("") is True

    def test_live_account_u_prefix_is_not_paper(self):
        assert is_paper_account_id("U1234567") is False

    def test_live_account_mixed_case_is_not_paper(self):
        assert is_paper_account_id("u1234567") is False

    def test_unknown_prefix_is_not_paper(self):
        assert is_paper_account_id("F9999999") is False


# ---------------------------------------------------------------------------
# GET /broker/health — response shape
# ---------------------------------------------------------------------------

class TestBrokerHealthShape:
    """GET /broker/health must always return a correctly shaped response."""

    def test_health_returns_200(self, client):
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            response = client.get("/broker/health")
        assert response.status_code == 200

    def test_health_has_required_keys(self, client):
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        required = {"status", "mode_guard_ok", "gateway_reachable", "gateway_url",
                    "account_id", "account_is_paper", "broker_mode"}
        assert required.issubset(data.keys())

    def test_broker_mode_nested_keys_present(self, client):
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        bm = data["broker_mode"]
        assert set(bm.keys()) == {"broker", "mode", "live_execution_enabled", "paper_trading_enabled"}


# ---------------------------------------------------------------------------
# GET /broker/health — status values
# ---------------------------------------------------------------------------

class TestBrokerHealthStatus:
    """status field must reflect the combined check outcome."""

    def test_paper_ready_when_all_checks_pass(self, client, monkeypatch):
        """status=paper_ready when guard OK, gateway reachable, DU account."""
        monkeypatch.setenv("IBKR_ACCOUNT_ID", "DUP153837")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        assert data["status"] == "paper_ready"
        assert data["mode_guard_ok"] is True
        assert data["gateway_reachable"] is True
        assert data["account_is_paper"] is True

    def test_paper_config_only_when_gateway_unreachable(self, client, monkeypatch):
        """status=paper_config_only when guard OK but gateway not reachable."""
        monkeypatch.setenv("IBKR_ACCOUNT_ID", "DUP153837")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["status"] == "paper_config_only"
        assert data["mode_guard_ok"] is True
        assert data["gateway_reachable"] is False

    def test_paper_config_only_when_no_account_configured(self, client, monkeypatch):
        """status=paper_config_only when account not yet set and gateway down."""
        monkeypatch.setenv("IBKR_ACCOUNT_ID", "")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["status"] == "paper_config_only"
        assert data["account_is_paper"] is True  # empty = safe

    def test_misconfigured_when_live_execution_enabled(self, client, monkeypatch):
        """status=misconfigured when LIVE_EXECUTION_ENABLED=true."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["status"] == "misconfigured"
        assert data["mode_guard_ok"] is False

    def test_misconfigured_when_broker_mode_live(self, client, monkeypatch):
        """status=misconfigured when BROKER_MODE=live."""
        monkeypatch.setenv("BROKER_MODE", "live")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["status"] == "misconfigured"
        assert data["mode_guard_ok"] is False

    def test_misconfigured_when_ibkr_account_type_live(self, client, monkeypatch):
        """status=misconfigured when IBKR_ACCOUNT_TYPE=live."""
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["status"] == "misconfigured"
        assert data["mode_guard_ok"] is False

    def test_misconfigured_even_when_gateway_reachable(self, client, monkeypatch):
        """Gateway being up does NOT override a misconfigured status."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        assert data["status"] == "misconfigured"

    def test_account_is_paper_false_for_live_account_id(self, client, monkeypatch):
        """account_is_paper must be False for a live (U-prefix) account ID."""
        monkeypatch.setenv("IBKR_ACCOUNT_ID", "U1234567")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["account_is_paper"] is False
        # Should still be paper_config_only (guard is OK; account_is_paper doesn't
        # change the mode_guard_ok field — that's governed by env vars only)
        assert data["mode_guard_ok"] is True

    def test_gateway_url_echoed_in_response(self, client, monkeypatch):
        """gateway_url in response must match IBKR_GATEWAY_URL setting."""
        monkeypatch.setenv("IBKR_GATEWAY_URL", "https://localhost:9999/v1/api")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["gateway_url"] == "https://localhost:9999/v1/api"

    def test_broker_mode_metadata_in_response(self, client):
        """broker_mode nested object must reflect current env state."""
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        bm = data["broker_mode"]
        assert bm["mode"] == "paper"
        assert bm["live_execution_enabled"] is False
        assert bm["paper_trading_enabled"] is True

    def test_live_ready_when_all_live_values_set(self, client, monkeypatch):
        """status=live_ready when all three live values set and gateway reachable."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "live")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        monkeypatch.setenv("IBKR_ACCOUNT_ID", "U1234567")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        assert data["status"] == "live_ready"
        assert data["mode_guard_ok"] is True
        assert data["gateway_reachable"] is True
        bm = data["broker_mode"]
        assert bm["mode"] == "live"
        assert bm["live_execution_enabled"] is True
        assert bm["paper_trading_enabled"] is False

    def test_live_config_only_when_live_values_set_but_gateway_down(self, client, monkeypatch):
        """status=live_config_only when all three live values set but gateway unreachable."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "live")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)):
            data = client.get("/broker/health").json()
        assert data["status"] == "live_config_only"
        assert data["mode_guard_ok"] is True
        assert data["gateway_reachable"] is False
        bm = data["broker_mode"]
        assert bm["mode"] == "live"


class TestBrokerReadinessChecklist:
    def test_readiness_healthy_paper_config_is_green(self, client, monkeypatch):
        monkeypatch.setenv("IBKR_ACCOUNT_ID", "DUP153837")
        monkeypatch.setenv("BROKER_PROVIDER", "tws")
        monkeypatch.setenv("TWS_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "paper")
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
        monkeypatch.setenv("PAPER_TRADING_ENABLED", "true")
        monkeypatch.setenv("AUTO_PAPER_ENABLED", "true")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        checklist = data["broker_readiness"]
        assert checklist["overall_status"] == "green"
        assert checklist["items"]
        assert all(item["status"] == "green" for item in checklist["items"])

    def test_readiness_live_execution_enabled_is_red(self, client, monkeypatch):
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        checklist = data["broker_readiness"]
        item = next(i for i in checklist["items"] if i["key"] == "live_execution_disabled")
        assert item["status"] == "red"
        assert "LIVE_EXECUTION_ENABLED=false" in item["suggested_action"]

    def test_readiness_non_paper_mode_is_red(self, client, monkeypatch):
        monkeypatch.setenv("BROKER_MODE", "live")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        checklist = data["broker_readiness"]
        item = next(i for i in checklist["items"] if i["key"] == "broker_mode_paper")
        assert item["status"] == "red"

    def test_readiness_tws_unavailable_is_yellow_with_action(self, client):
        class _DisconnectedService:
            def get_runtime_diagnostics(self):
                return {
                    "tws_runtime_client_id": None,
                    "tws_connection_state": "disconnected",
                    "tws_last_error_code": None,
                    "tws_last_error_message": None,
                }

        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)), patch(
            "app.api.routes.broker.get_broker_service",
            return_value=_DisconnectedService(),
        ):
            data = client.get("/broker/health").json()
        checklist = data["broker_readiness"]
        item = next(i for i in checklist["items"] if i["key"] == "tws_reachable")
        assert item["status"] in {"yellow", "red"}
        assert "TWS/Gateway" in item["suggested_action"]

    def test_readiness_account_not_visible_is_red(self, client, monkeypatch):
        monkeypatch.setenv("IBKR_ACCOUNT_ID", "U1234567")
        get_settings.cache_clear()
        with patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        checklist = data["broker_readiness"]
        item = next(i for i in checklist["items"] if i["key"] == "paper_account_visible")
        assert item["status"] == "red"

    def test_readiness_client_id_contention_is_red(self, client):
        class _StubService:
            def get_runtime_diagnostics(self):
                return {
                    "tws_runtime_client_id": 43,
                    "tws_connection_state": "error",
                    "tws_last_error_code": "326",
                    "tws_last_error_message": "client id is already in use",
                }

        with patch("app.api.routes.broker.get_broker_service", return_value=_StubService()), patch(
            "app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=False)
        ):
            data = client.get("/broker/health").json()
        checklist = data["broker_readiness"]
        item = next(i for i in checklist["items"] if i["key"] == "client_id_contention_inactive")
        assert item["status"] == "red"
        assert "duplicate" in item["suggested_action"].lower() or "contention" in item["suggested_action"].lower()

    def test_readiness_audit_alignment_warning_maps_yellow(self, client):
        with patch(
            "app.api.routes.broker.get_auto_paper_status_card",
            return_value={
                "next_run_guidance": {"paper_normal_mode_active": True},
                "candidate_queue": {"eligible_count": 1},
                "audit_alignment": {"status": "warning"},
                "latest_paper_order": None,
            },
        ), patch("app.api.routes.broker.check_ibkr_gateway", new=AsyncMock(return_value=True)):
            data = client.get("/broker/health").json()
        checklist = data["broker_readiness"]
        item = next(i for i in checklist["items"] if i["key"] == "audit_alignment_visible")
        assert item["status"] in {"yellow", "red"}
