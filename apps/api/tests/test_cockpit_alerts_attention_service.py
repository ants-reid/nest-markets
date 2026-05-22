from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.cockpit_alerts_attention_service import (
    get_cockpit_alerts_needing_attention,
)


class _DummySession:
    pass


def _incident(*, severity: str, source: str, code: str, title: str, created_at: datetime):
    return SimpleNamespace(
        id=uuid4(),
        severity=severity,
        source=source,
        code=code,
        title=title,
        detail=None,
        occurred_at=None,
        created_at=created_at,
    )


def _monitor_row(*, name: str, status: str, checked_at: datetime):
    return SimpleNamespace(
        name=name,
        status=status,
        detail=f"{name} reported {status}",
        latency_ms=25.0,
        checked_at=checked_at.isoformat(),
    )


def _stale_order(*, status: str, submitted_at: datetime):
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        submitted_at=submitted_at,
        timestamp=None,
        created_at=submitted_at,
        asset_id=None,
    )


def test_empty_response_returns_safe_summary_and_limitations(monkeypatch):
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_assets", lambda session: ({}, {}, {}))
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_active_alerts", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_notifications", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_incidents", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_health_snapshot", lambda: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_stale_paper_orders", lambda session, now_utc: [])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_risk_status",
        lambda session: SimpleNamespace(risk_limits_configured=True, missing_limits=[], configured_limits={}, note="risk ok"),
    )
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_trading_halt_status",
        lambda session: SimpleNamespace(emergency_stop_active=False, active_halt=None, blocked_reason=None, status="clear"),
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_recent_risk_decisions", lambda session: [])

    report = get_cockpit_alerts_needing_attention(_DummySession(), now_utc=now)

    assert report.mode == "paper"
    assert report.summary.total_items == 0
    assert report.attention_items == []
    assert report.limitations
    assert report.recommended_review_actions


def test_active_alerts_and_unresolved_incidents_are_surfaced_read_only(monkeypatch):
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    asset_id = str(uuid4())

    alert = SimpleNamespace(
        alert_id="a1",
        rule_id=uuid4(),
        execution_id=uuid4(),
        asset="AAPL",
        status="rejected",
        message="AAPL execution was rejected",
        level="warning",
    )
    notification = SimpleNamespace(
        notification_id="n1",
        alert_id="a1",
        rule_id=uuid4(),
        execution_id=uuid4(),
        asset="AAPL",
        status="rejected",
        message="Unread alert for AAPL",
        level="warning",
        is_read=False,
    )

    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_assets",
        lambda session: ({asset_id: "AAPL"}, {asset_id: "Apple Inc."}, {"AAPL": asset_id}),
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_active_alerts", lambda session: [alert])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_notifications", lambda session: [notification])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_incidents",
        lambda session: [
            _incident(
                severity="error",
                source="worker",
                code="worker.failure",
                title="Worker failure",
                created_at=now - timedelta(minutes=3),
            )
        ],
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_health_snapshot", lambda: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_stale_paper_orders", lambda session, now_utc: [])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_risk_status",
        lambda session: SimpleNamespace(risk_limits_configured=True, missing_limits=[], configured_limits={}, note="risk ok"),
    )
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_trading_halt_status",
        lambda session: SimpleNamespace(emergency_stop_active=False, active_halt=None, blocked_reason=None, status="clear"),
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_recent_risk_decisions", lambda session: [])

    report = get_cockpit_alerts_needing_attention(_DummySession(), now_utc=now)

    attention_types = {item.attention_type for item in report.attention_items}
    assert "active_alert" in attention_types
    assert "unresolved_incident" in attention_types
    assert all(item.is_actionable is False for item in report.attention_items)
    assert any(item.has_asset_context is True for item in report.attention_items if item.source in {"alert", "notification"})


def test_monitor_degraded_risk_attention_and_trading_halt_are_surfaced(monkeypatch):
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_assets", lambda session: ({}, {}, {}))
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_active_alerts", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_notifications", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_incidents", lambda session: [])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_health_snapshot",
        lambda: [_monitor_row(name="feeds_in.polygon_provider", status="down", checked_at=now)],
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_stale_paper_orders", lambda session, now_utc: [])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_risk_status",
        lambda session: SimpleNamespace(
            risk_limits_configured=False,
            missing_limits=["max_order_notional", "max_open_positions"],
            configured_limits={},
            note="Risk limits are configured for future enforcement but are not yet wired into broker submission.",
        ),
    )
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_trading_halt_status",
        lambda session: SimpleNamespace(
            emergency_stop_active=True,
            active_halt=SimpleNamespace(triggered_at=now - timedelta(minutes=5)),
            blocked_reason="Trading halt active (manual) for scope 'global': test.",
            status="active",
        ),
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_recent_risk_decisions", lambda session: [])

    report = get_cockpit_alerts_needing_attention(_DummySession(), now_utc=now)
    attention_types = {item.attention_type for item in report.attention_items}

    assert "monitor_degraded" in attention_types
    assert "risk_attention" in attention_types
    assert "trading_halt" in attention_types


def test_stale_data_and_missing_optional_fields_are_handled_safely(monkeypatch):
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_assets", lambda session: ({}, {}, {}))
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_active_alerts", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_notifications", lambda session: [])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_incidents",
        lambda session: [
            _incident(
                severity="warn",
                source="monitor",
                code="feed.stale",
                title="Feed stale",
                created_at=now - timedelta(minutes=8),
            )
        ],
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_health_snapshot", lambda: [])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_stale_paper_orders",
        lambda session, now_utc: [_stale_order(status="submitted", submitted_at=now - timedelta(hours=8))],
    )
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_risk_status",
        lambda session: SimpleNamespace(risk_limits_configured=True, missing_limits=[], configured_limits={}, note="risk ok"),
    )
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_trading_halt_status",
        lambda session: SimpleNamespace(emergency_stop_active=False, active_halt=None, blocked_reason=None, status="clear"),
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_recent_risk_decisions", lambda session: [])

    report = get_cockpit_alerts_needing_attention(_DummySession(), now_utc=now)

    assert any(item.attention_type == "stale_data" for item in report.attention_items)
    assert report.summary.stale_data >= 1


def test_service_does_not_call_mutation_paths(monkeypatch):
    now = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_assets", lambda session: ({}, {}, {}))
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_active_alerts", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_notifications", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_incidents", lambda session: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_health_snapshot", lambda: [])
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_stale_paper_orders", lambda session, now_utc: [])
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_risk_status",
        lambda session: SimpleNamespace(risk_limits_configured=True, missing_limits=[], configured_limits={}, note="risk ok"),
    )
    monkeypatch.setattr(
        "app.services.cockpit_alerts_attention_service._load_trading_halt_status",
        lambda session: SimpleNamespace(emergency_stop_active=False, active_halt=None, blocked_reason=None, status="clear"),
    )
    monkeypatch.setattr("app.services.cockpit_alerts_attention_service._load_recent_risk_decisions", lambda session: [])

    def _boom(*args, **kwargs):
        raise AssertionError("mutation path should not be invoked")

    monkeypatch.setattr("app.services.persistence_alert_service.PersistenceAlertService.acknowledge_rule", _boom)
    monkeypatch.setattr("app.services.persistence_notification_service.PersistenceNotificationService.mark_as_read", _boom)
    monkeypatch.setattr("app.services.trading_halt_service.TradingHaltService.resolve_halt", _boom)

    report = get_cockpit_alerts_needing_attention(_DummySession(), now_utc=now)

    assert report.mode == "paper"
