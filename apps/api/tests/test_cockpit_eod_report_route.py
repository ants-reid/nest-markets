from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import create_app


def _sample_payload() -> dict:
    return {
        "report_date": "2026-05-22",
        "generated_at": "2026-05-22T20:15:00+00:00",
        "mode": "paper",
        "summary": {
            "headline": "Paper-mode end-of-day recap for operator review.",
            "opened_today": 2,
            "closed_today": 1,
            "open_positions_now": 1,
            "alerts_needing_attention": 1,
            "lessons_available": 1,
        },
        "paper_activity": {
            "opened_today": 2,
            "closed_today": 1,
            "current_open_positions": 1,
        },
        "pnl": {
            "realized_day": 12.5,
            "unrealized_snapshot": 4.25,
            "realized_basis": "closed_positions_today",
            "unrealized_basis": "open_positions_snapshot",
        },
        "open_positions": {
            "count": 1,
            "items": [
                {
                    "asset_symbol": "AAPL",
                    "side": "long",
                    "qty": 1.0,
                    "opened_at": "2026-05-22T18:00:00+00:00",
                    "unrealized_pnl": 4.25,
                }
            ],
        },
        "closed_positions": {
            "count": 1,
            "wins": 1,
            "losses": 0,
            "flat": 0,
            "unknown": 0,
            "best_trade": {
                "asset_symbol": "AAPL",
                "side": "long",
                "opened_at": "2026-05-22T15:00:00+00:00",
                "closed_at": "2026-05-22T17:00:00+00:00",
                "realized_pnl": 12.5,
                "close_reason": "target_hit",
            },
            "worst_trade": {
                "asset_symbol": "AAPL",
                "side": "long",
                "opened_at": "2026-05-22T15:00:00+00:00",
                "closed_at": "2026-05-22T17:00:00+00:00",
                "realized_pnl": 12.5,
                "close_reason": "target_hit",
            },
            "items": [
                {
                    "asset_symbol": "AAPL",
                    "side": "long",
                    "opened_at": "2026-05-22T15:00:00+00:00",
                    "closed_at": "2026-05-22T17:00:00+00:00",
                    "realized_pnl": 12.5,
                    "close_reason": "target_hit",
                }
            ],
        },
        "alerts_or_incidents": [
            {
                "severity": "critical",
                "code": "monitor.feed_down",
                "title": "Feed degraded",
                "source": "monitor",
                "created_at": "2026-05-22T18:30:00+00:00",
                "detail": "Primary feed stalled.",
            }
        ],
        "monitor_notes": [
            {
                "title": "Feed degraded",
                "detail": "Primary feed stalled.",
                "severity": "critical",
                "created_at": "2026-05-22T18:30:00+00:00",
            }
        ],
        "lessons": [
            {
                "title": "Directional accuracy",
                "detail": "1/1 closed outcomes matched the predicted direction today.",
                "evidence_count": 1,
            }
        ],
        "recommended_actions": [
            "Review the highest-severity incidents in Cockpit Notifications before the next paper session."
        ],
        "limitations": [],
    }


def test_cockpit_eod_report_route_returns_stable_schema(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr("app.api.routes.cockpit_eod_report.get_cockpit_eod_report", lambda session: _sample_payload())
    try:
        client = TestClient(app)
        response = client.get("/cockpit/eod-report")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
    body = response.json()
    for key in (
        "report_date",
        "generated_at",
        "mode",
        "summary",
        "paper_activity",
        "pnl",
        "open_positions",
        "closed_positions",
        "alerts_or_incidents",
        "monitor_notes",
        "lessons",
        "recommended_actions",
        "limitations",
    ):
        assert key in body, f"missing key: {key}"
    assert body["mode"] == "paper"


def test_cockpit_eod_report_route_does_not_call_broker_or_live_paths(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr("app.api.routes.cockpit_eod_report.get_cockpit_eod_report", lambda session: _sample_payload())

    def _boom(*args, **kwargs):
        raise AssertionError("broker or live execution path should not be invoked")

    monkeypatch.setattr("app.services.broker_service.BrokerService.submit_auto_order", _boom)
    monkeypatch.setattr("app.services.live_execution_service.LiveExecutionService.submit", _boom)
    try:
        client = TestClient(app)
        response = client.get("/cockpit/eod-report")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text