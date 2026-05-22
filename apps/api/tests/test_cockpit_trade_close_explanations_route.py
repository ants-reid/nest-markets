from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import create_app


def _sample_payload() -> dict:
    return {
        "generated_at": "2026-05-22T21:00:00+00:00",
        "mode": "paper",
        "summary": {
            "headline": "Read-only explanations for recently closed paper trades.",
            "total_closed_trades": 1,
            "known_close_labels": 1,
            "unknown_close_labels": 0,
            "profitable_trades": 1,
            "losing_trades": 0,
            "flat_trades": 0,
            "setup_matched": 1,
            "setup_mismatched": 0,
            "setup_unknown": 0,
        },
        "explanations": [
            {
                "id": "a7616e00-0f87-4cca-8a3f-4463f634d7fd",
                "paper_order_id": "c9a88014-0d9f-4477-a810-c9a3d4f335b7",
                "position_id": "a7616e00-0f87-4cca-8a3f-4463f634d7fd",
                "symbol": "AAPL",
                "opened_at": "2026-05-22T18:00:00+00:00",
                "closed_at": "2026-05-22T20:00:00+00:00",
                "status": "closed",
                "close_label": "target_hit",
                "close_reason": "target hit",
                "result_summary": "Close label target_hit; realized gain 10.00; setup match matched.",
                "realized_pnl": 10.0,
                "outcome_match": "matched",
                "evidence": ["position_status=closed"],
                "missing_data": [],
                "learning_note": "Target-aligned exits can be reviewed for repeatable setup quality before increasing confidence.",
                "is_actionable": False,
            }
        ],
        "limitations": [],
        "recommended_review_actions": [
            "Review unknown and risk_close labels first, then compare evidence with execution and risk logs."
        ],
    }


def test_trade_close_explanations_route_returns_stable_schema(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_trade_close_explanations.get_cockpit_trade_close_explanations",
        lambda session: _sample_payload(),
    )
    try:
        client = TestClient(app)
        response = client.get("/cockpit/trade-close-explanations")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
    body = response.json()
    for key in (
        "generated_at",
        "mode",
        "summary",
        "explanations",
        "limitations",
        "recommended_review_actions",
    ):
        assert key in body, f"missing key: {key}"
    assert body["mode"] == "paper"
    assert all(item["is_actionable"] is False for item in body["explanations"])


def test_trade_close_explanations_route_does_not_call_broker_or_mutation_paths(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_trade_close_explanations.get_cockpit_trade_close_explanations",
        lambda session: _sample_payload(),
    )

    def _boom(*args, **kwargs):
        raise AssertionError("broker/live/mutation path should not be invoked")

    monkeypatch.setattr("app.services.broker_service.BrokerService.submit_auto_order", _boom)
    monkeypatch.setattr("app.services.live_execution_service.LiveExecutionService.submit", _boom)
    monkeypatch.setattr("app.services.paper_execution_service.PaperExecutionService.close_order", _boom)
    monkeypatch.setattr("app.services.position_service.PositionService.close_position", _boom)

    try:
        client = TestClient(app)
        response = client.get("/cockpit/trade-close-explanations")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
