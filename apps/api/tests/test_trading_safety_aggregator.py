"""Tests for MH-MON-04 — trading safety aggregator."""

from __future__ import annotations

import pytest

from app.services import health_registry as hr
from app.services import trading_safety_aggregator as tsa


@pytest.fixture
def _clean_registry():
    snapshot = dict(hr._REGISTRY)
    hr._REGISTRY.clear()
    yield
    hr._REGISTRY.clear()
    hr._REGISTRY.update(snapshot)


def _ok_probe(name: str):
    def probe() -> hr.ProbeResult:
        return hr.ProbeResult(status="ok", detail="ok")

    return probe


def _down_probe(name: str):
    def probe() -> hr.ProbeResult:
        return hr.ProbeResult(status="down", detail="bad")

    return probe


def _degraded_probe(name: str):
    def probe() -> hr.ProbeResult:
        return hr.ProbeResult(status="degraded", detail="meh")

    return probe


def _register_all_core_ok():
    for name in tsa.CORE_PROBE_NAMES:
        hr.register_probe(name, _ok_probe(name))


class _FakeHaltStatus:
    def __init__(self, active: bool, reason=None):
        self.emergency_stop_active = active
        self.blocked_reason = reason


class _FakeHaltService:
    def __init__(self, session):
        pass

    def get_status(self, scope: str = "global"):
        return _FakeHaltStatus(False, None)


class _FakeHaltServiceActive(_FakeHaltService):
    def get_status(self, scope: str = "global"):
        return _FakeHaltStatus(True, "manual_pause")


class _FakeState:
    def __init__(self, **kw):
        self.trading_mode = kw.get("trading_mode", "paper")
        self.execution_control = kw.get("execution_control", "manual")
        self.arming_state = kw.get("arming_state", "armed")
        self.auto_trading_allowed = kw.get("auto_trading_allowed", False)


def _patch_halt(monkeypatch, halt_cls=_FakeHaltService):
    monkeypatch.setattr(
        "app.services.trading_halt_service.TradingHaltService",
        halt_cls,
        raising=True,
    )

    class _SessionFactory:
        def __call__(self):
            class _S:
                def close(self_inner):
                    pass

            return _S()

    monkeypatch.setattr(
        "app.db.session.SessionLocal", _SessionFactory(), raising=True
    )


def _patch_control(monkeypatch, **kw):
    state = _FakeState(**kw)
    monkeypatch.setattr(
        "app.services.trading_control_service.get_trading_mode",
        lambda: state,
        raising=True,
    )


def test_safe_when_all_ok(_clean_registry, monkeypatch):
    _register_all_core_ok()
    _patch_halt(monkeypatch)
    _patch_control(monkeypatch)

    decision = tsa.evaluate_trading_safety()

    assert decision.safe_to_enable_enforcement is True
    assert decision.overall_health == "ok"
    assert decision.halt_active is False
    assert decision.auto_trading_allowed is False
    assert decision.blocking_reasons == []
    assert decision.checked_at  # ISO timestamp present


def test_blocks_on_active_halt(_clean_registry, monkeypatch):
    _register_all_core_ok()
    _patch_halt(monkeypatch, _FakeHaltServiceActive)
    _patch_control(monkeypatch)

    decision = tsa.evaluate_trading_safety()

    assert decision.safe_to_enable_enforcement is False
    assert decision.halt_active is True
    assert decision.halt_reason == "manual_pause"
    assert "trading_halt_active" in decision.blocking_reasons


def test_blocks_on_core_probe_down(_clean_registry, monkeypatch):
    # Register all core probes but flip one to 'down'.
    for name in tsa.CORE_PROBE_NAMES:
        if name == "database":
            hr.register_probe(name, _down_probe(name))
        else:
            hr.register_probe(name, _ok_probe(name))
    _patch_halt(monkeypatch)
    _patch_control(monkeypatch)

    decision = tsa.evaluate_trading_safety()

    assert decision.safe_to_enable_enforcement is False
    assert decision.overall_health == "down"
    assert any(
        r.startswith("core_probe_unhealthy:database") for r in decision.blocking_reasons
    )


def test_advisory_on_core_probe_degraded(_clean_registry, monkeypatch):
    for name in tsa.CORE_PROBE_NAMES:
        if name == "feeds_in.polygon_provider":
            hr.register_probe(name, _degraded_probe(name))
        else:
            hr.register_probe(name, _ok_probe(name))
    _patch_halt(monkeypatch)
    _patch_control(monkeypatch)

    decision = tsa.evaluate_trading_safety()

    # Degraded core probe -> not safe (overall is degraded, not "ok"), but
    # appears in advisory_reasons not blocking.
    assert decision.safe_to_enable_enforcement is False
    assert decision.overall_health == "degraded"
    assert any(
        r.startswith("core_probe_degraded:feeds_in.polygon_provider")
        for r in decision.advisory_reasons
    )
    assert decision.blocking_reasons == []


def test_blocks_when_auto_trading_unexpectedly_true(_clean_registry, monkeypatch):
    _register_all_core_ok()
    _patch_halt(monkeypatch)
    _patch_control(monkeypatch, auto_trading_allowed=True)

    decision = tsa.evaluate_trading_safety()

    assert decision.safe_to_enable_enforcement is False
    assert "auto_trading_allowed_unexpectedly_true" in decision.blocking_reasons


def test_advisory_when_core_probe_missing(_clean_registry, monkeypatch):
    # Register only one core probe; the rest are missing.
    hr.register_probe("database", _ok_probe("database"))
    _patch_halt(monkeypatch)
    _patch_control(monkeypatch)

    decision = tsa.evaluate_trading_safety()

    missing = [r for r in decision.advisory_reasons if r.startswith("core_probe_missing:")]
    assert len(missing) >= 1


def test_to_dict_is_json_safe(_clean_registry, monkeypatch):
    _register_all_core_ok()
    _patch_halt(monkeypatch)
    _patch_control(monkeypatch)

    payload = tsa.evaluate_trading_safety().to_dict()
    assert isinstance(payload, dict)
    assert "safe_to_enable_enforcement" in payload
    assert "blocking_reasons" in payload
    assert "advisory_reasons" in payload
    assert "health_summary" in payload
    assert "checked_at" in payload
