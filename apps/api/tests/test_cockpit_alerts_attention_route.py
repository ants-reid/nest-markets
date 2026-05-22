from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import create_app


def _sample_payload() -> dict:
    return {
        "generated_at": "2026-05-22T23:10:00+00:00",
        "mode": "paper",
        "summary": {
            "headline": "Read-only paper attention queue for alerts, incidents, monitor health, and risk context.",
            "total_items": 2,
            "high_priority": 1,
            "medium_priority": 1,
            "low_priority": 0,
            "unknown_priority": 0,
            "active_alerts": 1,
            "unresolved_incidents": 0,
            "monitor_degraded": 1,
            "stale_data": 0,
            "risk_attention": 0,
            "trading_halt": 0,
            "missing_context": 0,
        },
        "attention_items": [
            {
                "id": "alert:a1",
                "source": "alert",
                "title": "Active alert for AAPL",
                "message": "AAPL execution was rejected",
                "priority": "high",
                "status": "rejected",
                "detected_at": None,
                "attention_type": "active_alert",
                "evidence": ["rule_id:x", "execution_id:y"],
                "missing_data": ["detected_at unavailable in active alert record"],
                "recommended_review_action": "Review related paper execution context and risk notes before taking any manual next step.",
                "is_actionable": False,
            },
            {
                "id": "monitor:feeds_in.polygon_provider",
                "source": "monitor",
                "title": "Monitor status down: feeds_in.polygon_provider",
                "message": "Probe failed",
                "priority": "medium",
                "status": "down",
                "detected_at": "2026-05-22T23:09:00+00:00",
                "attention_type": "monitor_degraded",
                "evidence": ["probe:feeds_in.polygon_provider"],
                "missing_data": [],
                "recommended_review_action": "Review monitor probe diagnostics and confirm feed/provider stability.",
                "is_actionable": False,
            },
        ],
        "grouped_by_priority": [
            {"group": "high", "count": 1, "item_ids": ["alert:a1"]},
            {"group": "medium", "count": 1, "item_ids": ["monitor:feeds_in.polygon_provider"]},
        ],
        "grouped_by_source": [
            {"group": "alert", "count": 1, "item_ids": ["alert:a1"]},
            {"group": "monitor", "count": 1, "item_ids": ["monitor:feeds_in.polygon_provider"]},
        ],
        "monitor_notes": [],
        "risk_notes": [],
        "limitations": [],
        "recommended_review_actions": [
            "Start with high-priority items, then work through medium-priority monitor and risk notes.",
        ],
    }


def test_alerts_attention_route_returns_stable_schema(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_alerts_needing_attention.get_cockpit_alerts_needing_attention",
        lambda session: _sample_payload(),
    )
    try:
        client = TestClient(app)
        response = client.get("/cockpit/alerts-needing-attention")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
    body = response.json()
    for key in (
        "generated_at",
        "mode",
        "summary",
        "attention_items",
        "grouped_by_priority",
        "grouped_by_source",
        "monitor_notes",
        "risk_notes",
        "limitations",
        "recommended_review_actions",
    ):
        assert key in body, f"missing key: {key}"
    assert body["mode"] == "paper"
    assert all(item["is_actionable"] is False for item in body["attention_items"])


def test_alerts_attention_route_does_not_call_execution_or_mutation_paths(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_alerts_needing_attention.get_cockpit_alerts_needing_attention",
        lambda session: _sample_payload(),
    )

    def _boom(*args, **kwargs):
        raise AssertionError("execution/mutation path should not be invoked")

    monkeypatch.setattr("app.services.broker_service.BrokerService.submit_auto_order", _boom)
    monkeypatch.setattr("app.services.live_execution_service.LiveExecutionService.submit", _boom)
    monkeypatch.setattr("app.services.paper_execution_service.PaperExecutionService.close_order", _boom)
    monkeypatch.setattr("app.services.position_service.PositionService.close_position", _boom)
    monkeypatch.setattr("app.services.persistence_alert_service.PersistenceAlertService.acknowledge_rule", _boom)
    monkeypatch.setattr("app.services.persistence_notification_service.PersistenceNotificationService.mark_as_read", _boom)
    monkeypatch.setattr("app.services.trading_halt_service.TradingHaltService.resolve_halt", _boom)

    try:
        client = TestClient(app)
        response = client.get("/cockpit/alerts-needing-attention")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
