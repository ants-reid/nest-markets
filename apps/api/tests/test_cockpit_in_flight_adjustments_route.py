from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import create_app


def _sample_payload() -> dict:
    return {
        "generated_at": "2026-05-22T20:15:00+00:00",
        "mode": "paper",
        "summary": {
            "headline": "Read-only in-flight paper adjustments watchlist for operator review.",
            "total_items": 2,
            "open_positions": 1,
            "open_orders": 1,
            "active_recommendations": 0,
            "watch_only": 0,
            "review_required": 2,
            "high_attention": 1,
        },
        "items": [
            {
                "id": "3f15f765-3f8e-4f7d-a511-cb90b0f03a13",
                "item_type": "paper_position",
                "symbol": "AAPL",
                "status": "open",
                "opened_at": "2026-05-22T18:00:00+00:00",
                "created_at": "2026-05-22T18:00:00+00:00",
                "current_state_summary": "AAPL long qty=1.0 entry=189.5",
                "attention_level": "high",
                "adjustment_label": "risk_attention",
                "reason": "Related risk decision is not approved and needs operator risk review.",
                "evidence": ["position_status=open", "risk_decision=rejected"],
                "missing_data": [],
                "recommended_review_action": "Review position risk context, stop/target geometry, and monitor health before next paper check.",
                "is_actionable": False,
            },
            {
                "id": "35fbeec8-0076-4c6e-a83d-20b39bc513a4",
                "item_type": "paper_order",
                "symbol": "AAPL",
                "status": "accepted",
                "opened_at": None,
                "created_at": "2026-05-22T20:00:00+00:00",
                "current_state_summary": "AAPL buy qty=1.0 type=limit",
                "attention_level": "medium",
                "adjustment_label": "review_required",
                "reason": "Paper order is active and should be reviewed in context.",
                "evidence": ["order_status=accepted"],
                "missing_data": [],
                "recommended_review_action": "Review order lifecycle and risk gate notes before deciding whether to keep monitoring.",
                "is_actionable": False,
            },
        ],
        "monitor_notes": [
            {
                "title": "Feed degraded",
                "detail": "Primary feed stalled.",
                "severity": "critical",
                "created_at": "2026-05-22T19:45:00+00:00",
            }
        ],
        "risk_notes": ["Risk decision rejected for test-signal: spread_too_wide."],
        "limitations": [],
        "recommended_review_actions": [
            "Start with high-attention items, then move through review_required and stale_data labels."
        ],
    }


def test_cockpit_in_flight_adjustments_route_returns_stable_schema(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_in_flight_adjustments.get_cockpit_in_flight_adjustments",
        lambda session: _sample_payload(),
    )
    try:
        client = TestClient(app)
        response = client.get("/cockpit/in-flight-adjustments")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
    body = response.json()
    for key in (
        "generated_at",
        "mode",
        "summary",
        "items",
        "monitor_notes",
        "risk_notes",
        "limitations",
        "recommended_review_actions",
    ):
        assert key in body, f"missing key: {key}"
    assert body["mode"] == "paper"
    assert all(item["is_actionable"] is False for item in body["items"])


def test_cockpit_in_flight_adjustments_route_does_not_call_broker_or_live_paths(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_in_flight_adjustments.get_cockpit_in_flight_adjustments",
        lambda session: _sample_payload(),
    )

    def _boom(*args, **kwargs):
        raise AssertionError("broker or live execution path should not be invoked")

    monkeypatch.setattr("app.services.broker_service.BrokerService.submit_auto_order", _boom)
    monkeypatch.setattr("app.services.live_execution_service.LiveExecutionService.submit", _boom)
    monkeypatch.setattr("app.services.position_service.PositionService.close_position", _boom)
    try:
        client = TestClient(app)
        response = client.get("/cockpit/in-flight-adjustments")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
