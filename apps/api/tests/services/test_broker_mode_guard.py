"""Operational verification tests for broker_mode_guard.

MH-36: covers assert_paper_mode() and get_broker_mode_metadata() under all
relevant env configurations.

Guard semantics (must be consistent):
  PAPER MODE:  LIVE_EXECUTION_ENABLED=false, BROKER_MODE=paper, IBKR_ACCOUNT_TYPE=paper
  LIVE MODE:   LIVE_EXECUTION_ENABLED=true,  BROKER_MODE=live,   IBKR_ACCOUNT_TYPE=live
  INVALID:     Any mismatch of the above (no casual toggling allowed)
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, patch

from app.config import get_settings
from app.services.broker_mode_guard import (
    BrokerModeInconsistencyError,
    LiveExecutionBlockedError,
    assert_paper_mode,
    check_ibkr_gateway,
    get_broker_mode_metadata,
    is_live_mode_enabled,
    is_paper_account_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Ensure get_settings() re-reads the environment for every test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# assert_paper_mode — happy path
# ---------------------------------------------------------------------------

class TestAssertPaperModeAllowed:
    """assert_paper_mode() must not raise when env is in safe paper state."""

    def test_default_env_is_safe(self):
        """Default settings (all paper defaults) must pass without error."""
        assert_paper_mode()  # raises = test fails

    def test_explicit_paper_values_pass(self, monkeypatch):
        """Explicitly setting all three paper values must pass."""
        monkeypatch.setenv("BROKER_MODE", "paper")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "paper")
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
        get_settings.cache_clear()
        assert_paper_mode()  # must not raise

    def test_broker_mode_case_insensitive(self, monkeypatch):
        """BROKER_MODE=PAPER (uppercase) must be treated as safe."""
        monkeypatch.setenv("BROKER_MODE", "PAPER")
        get_settings.cache_clear()
        assert_paper_mode()

    def test_ibkr_account_type_case_insensitive(self, monkeypatch):
        """IBKR_ACCOUNT_TYPE=Paper (mixed case) must be treated as safe."""
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "Paper")
        get_settings.cache_clear()
        assert_paper_mode()


# ---------------------------------------------------------------------------
# assert_paper_mode — live mode enabled (new in MH-36)
# ---------------------------------------------------------------------------

class TestAssertLiveModeAllowed:
    """assert_paper_mode() must pass when all three live values are set correctly."""

    def test_all_three_live_values_pass(self, monkeypatch):
        """When all three are live, the guard must pass."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "live")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        assert_paper_mode()  # must not raise

    def test_live_mode_case_insensitive(self, monkeypatch):
        """BROKER_MODE=LIVE (uppercase) must be treated correctly."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "LIVE")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        assert_paper_mode()  # must not raise

    def test_is_live_mode_enabled_returns_true_for_live_config(self, monkeypatch):
        """is_live_mode_enabled() must return True when all three are live."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "live")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        assert is_live_mode_enabled() is True

    def test_is_live_mode_enabled_returns_false_for_paper(self):
        """is_live_mode_enabled() must return False for paper mode."""
        assert is_live_mode_enabled() is False


# ---------------------------------------------------------------------------
# assert_paper_mode — guard rejects mismatches
# ---------------------------------------------------------------------------

class TestAssertModeInconsistency:
    """assert_paper_mode() must reject any mismatch of paper/live config."""

    def test_live_execution_enabled_true_without_live_mode_rejected(self, monkeypatch):
        """LIVE_EXECUTION_ENABLED=true but BROKER_MODE=paper must be rejected."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "paper")
        get_settings.cache_clear()
        with pytest.raises(BrokerModeInconsistencyError):
            assert_paper_mode()

    def test_broker_mode_live_without_live_execution_enabled_rejected(self, monkeypatch):
        """BROKER_MODE=live but LIVE_EXECUTION_ENABLED=false must be rejected."""
        monkeypatch.setenv("BROKER_MODE", "live")
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "false")
        get_settings.cache_clear()
        with pytest.raises(BrokerModeInconsistencyError):
            assert_paper_mode()

    def test_ibkr_account_type_live_without_live_mode_rejected(self, monkeypatch):
        """IBKR_ACCOUNT_TYPE=live without live broker mode must be rejected."""
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        monkeypatch.setenv("BROKER_MODE", "paper")
        get_settings.cache_clear()
        with pytest.raises(BrokerModeInconsistencyError):
            assert_paper_mode()

    def test_partial_live_config_rejected(self, monkeypatch):
        """Only setting two out of three live values must be rejected."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "live")
        # IBKR_ACCOUNT_TYPE still defaults to "paper"
        get_settings.cache_clear()
        with pytest.raises(BrokerModeInconsistencyError):
            assert_paper_mode()

    def test_error_message_lists_valid_combinations(self, monkeypatch):
        """Error message must explain valid combinations."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "paper")
        get_settings.cache_clear()
        with pytest.raises(BrokerModeInconsistencyError) as exc_info:
            assert_paper_mode()
        msg = str(exc_info.value)
        assert "false" in msg.lower()  # paper mode mention
        assert "true" in msg.lower()   # live mode mention
        assert "Valid combinations" in msg


# ---------------------------------------------------------------------------
# Guard trip — exception names (aliases in MH-36)
# ---------------------------------------------------------------------------

class TestExceptionNames:
    """BrokerModeInconsistencyError and LiveExecutionBlockedError are the same."""

    def test_broker_mode_inconsistency_error_is_live_execution_blocked_error(self):
        """Both names must refer to the same exception class."""
        assert BrokerModeInconsistencyError is LiveExecutionBlockedError

    def test_guard_raises_live_execution_blocked_error(self, monkeypatch):
        """Guard raises LiveExecutionBlockedError for mismatched configs."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "paper")
        get_settings.cache_clear()
        with pytest.raises(LiveExecutionBlockedError):
            assert_paper_mode()

    def test_guard_raises_broker_mode_inconsistency_error(self, monkeypatch):
        """Guard raises error catchable as BrokerModeInconsistencyError."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "paper")
        get_settings.cache_clear()
        with pytest.raises(BrokerModeInconsistencyError):
            assert_paper_mode()


# ---------------------------------------------------------------------------
# get_broker_mode_metadata — structure & values
# ---------------------------------------------------------------------------

class TestGetBrokerModeMetadata:
    """get_broker_mode_metadata() must return correctly shaped dict."""

    def test_default_metadata_is_safe_paper(self):
        """Default metadata must reflect full paper mode."""
        meta = get_broker_mode_metadata()
        assert meta["broker"] == "ibkr"
        assert meta["mode"] == "paper"
        assert meta["live_execution_enabled"] is False
        assert meta["paper_trading_enabled"] is True

    def test_metadata_keys_always_present(self):
        """All four keys must always be present."""
        meta = get_broker_mode_metadata()
        assert set(meta.keys()) == {
            "broker",
            "mode",
            "live_execution_enabled",
            "paper_trading_enabled",
        }

    def test_mode_field_reflects_actual_configuration(self, monkeypatch):
        """mode field must show 'live' when all three live values are set."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "live")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        meta = get_broker_mode_metadata()
        assert meta["mode"] == "live"
        assert meta["live_execution_enabled"] is True
        assert meta["paper_trading_enabled"] is False

    def test_paper_trading_enabled_false_when_live_execution_enabled(self, monkeypatch):
        """paper_trading_enabled must be False when live mode is active."""
        monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
        monkeypatch.setenv("BROKER_MODE", "live")
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        meta = get_broker_mode_metadata()
        assert meta["paper_trading_enabled"] is False
        assert meta["live_execution_enabled"] is True

    def test_paper_trading_enabled_false_when_broker_mode_live_mismatch(self, monkeypatch):
        """paper_trading_enabled must be False when BROKER_MODE=live (even if mismatched)."""
        monkeypatch.setenv("BROKER_MODE", "live")
        get_settings.cache_clear()
        meta = get_broker_mode_metadata()
        assert meta["paper_trading_enabled"] is False

    def test_paper_trading_enabled_false_when_ibkr_account_type_live_mismatch(self, monkeypatch):
        """paper_trading_enabled must be False when IBKR_ACCOUNT_TYPE=live (even if mismatched)."""
        monkeypatch.setenv("IBKR_ACCOUNT_TYPE", "live")
        get_settings.cache_clear()
        meta = get_broker_mode_metadata()
        assert meta["paper_trading_enabled"] is False

    def test_broker_field_reflects_broker_provider_env(self, monkeypatch):
        """broker field must reflect BROKER_PROVIDER env var."""
        monkeypatch.setenv("BROKER_PROVIDER", "alpaca")
        get_settings.cache_clear()
        meta = get_broker_mode_metadata()
        assert meta["broker"] == "alpaca"

    def test_mode_field_reflects_broker_mode_env(self, monkeypatch):
        """mode field must reflect BROKER_MODE env var."""
        monkeypatch.setenv("BROKER_MODE", "live")
        get_settings.cache_clear()
        meta = get_broker_mode_metadata()
        assert meta["mode"] == "live"


# ---------------------------------------------------------------------------
# MH-27 helpers — gateway probe and account classifier
# ---------------------------------------------------------------------------

class TestCheckIbkrGateway:
    """check_ibkr_gateway() should classify gateway reachability robustly."""

    @pytest.mark.asyncio
    async def test_returns_true_for_non_5xx(self):
        """Any non-5xx response indicates the gateway is reachable."""
        with patch("app.services.broker_mode_guard.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=SimpleNamespace(status_code=401))

            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_client
            mock_cm.__aexit__.return_value = None
            mock_client_cls.return_value = mock_cm

            ok = await check_ibkr_gateway("https://localhost:5001/v1/api", timeout=0.1)

        assert ok is True

    @pytest.mark.asyncio
    async def test_returns_false_for_5xx(self):
        """5xx responses indicate the gateway is not healthy enough."""
        with patch("app.services.broker_mode_guard.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=SimpleNamespace(status_code=503))

            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_client
            mock_cm.__aexit__.return_value = None
            mock_client_cls.return_value = mock_cm

            ok = await check_ibkr_gateway("https://localhost:5001/v1/api", timeout=0.1)

        assert ok is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        """Network/SSL/timeout errors should be treated as unreachable."""
        with patch("app.services.broker_mode_guard.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=RuntimeError("boom"))

            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_client
            mock_cm.__aexit__.return_value = None
            mock_client_cls.return_value = mock_cm

            ok = await check_ibkr_gateway("https://localhost:5001/v1/api", timeout=0.1)

        assert ok is False


class TestIsPaperAccountId:
    """is_paper_account_id() should enforce DU-prefix semantics."""

    def test_du_prefix_is_paper(self):
        assert is_paper_account_id("DUP153837") is True

    def test_empty_string_treated_as_safe(self):
        assert is_paper_account_id("") is True

    def test_u_prefix_not_paper(self):
        assert is_paper_account_id("U1234567") is False
