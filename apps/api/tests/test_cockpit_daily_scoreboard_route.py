from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import create_app


def _sample_payload() -> dict:
    return {
        "report_date": "2026-05-22",
        "generated_at": "2026-05-22T21:00:00+00:00",
        "mode": "paper",
        "summary": {
            "headline": "Read-only daily paper-trading scoreboard for operator review.",
            "day_status": "green_day",
            "trades_opened_today": 2,
            "trades_closed_today": 1,
            "open_positions_now": 1,
        },
        "performance": {
            "realized_pnl_today": 12.5,
            "unrealized_pnl_snapshot": 3.0,
            "net_pnl_today": 15.5,
            "win_count": 1,
            "loss_count": 0,
            "flat_count": 0,
            "unknown_count": 0,
        },
        "activity": {
            "trades_opened_today": 2,
            "trades_closed_today": 1,
            "open_positions_now": 1,
        },
        "open_positions": {
            "count": 1,
            "long_count": 1,
            "short_count": 0,
        },
        "closed_positions": {
            "count": 1,
            "wins": 1,
            "losses": 0,
            "flat": 0,
            "unknown": 0,
        },
        "top_contributors": {
            "count": 1,
            "items": [
                {
                    "symbol": "AAPL",
                    "realized_pnl": 12.5,
                    "contribution_label": "positive",
                    "evidence": ["realized_pnl_sum_by_symbol"],
                }
            ],
        },
        "risk_and_monitor_notes": [],
        "review_priorities": [
            "Review top positive and negative contributors to compare setup quality and exit behavior.",
        ],
        "limitations": [],
    }


def test_daily_scoreboard_route_returns_stable_schema(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_daily_scoreboard.get_cockpit_daily_scoreboard",
        lambda session: _sample_payload(),
    )
    try:
        client = TestClient(app)
        response = client.get("/cockpit/daily-scoreboard")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
    body = response.json()
    for key in (
        "report_date",
        "generated_at",
        "mode",
        "summary",
        "performance",
        "activity",
        "open_positions",
        "closed_positions",
        "top_contributors",
        "risk_and_monitor_notes",
        "review_priorities",
        "limitations",
    ):
        assert key in body, f"missing key: {key}"
    assert body["mode"] == "paper"


def test_daily_scoreboard_route_does_not_call_broker_or_mutation_paths(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    monkeypatch.setattr(
        "app.api.routes.cockpit_daily_scoreboard.get_cockpit_daily_scoreboard",
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
        response = client.get("/cockpit/daily-scoreboard")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200, response.text
