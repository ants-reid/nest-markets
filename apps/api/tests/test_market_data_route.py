from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.routes import market_data as market_data_route
from app.db.models.news_article import NewsArticle
from app.db.session import get_db_session
from app.main import app
from app.schemas.risk_limits import RiskLimitStatusResponse
from app.schemas.trading_halt import TradingHaltStatusResponse
from app.services.worker_run_log_service import WorkerRunEntry
from app.workers.base_worker import WorkerResult


def _make_news(**kwargs) -> NewsArticle:
    defaults = dict(
        id=uuid.uuid4(),
        headline="AAPL beats earnings",
        source_name="Reuters",
        published_at=datetime.now(timezone.utc),
        url="https://example.com/aapl",
        tickers_json=["AAPL"],
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=NewsArticle)
    for key, value in defaults.items():
        setattr(obj, key, value)
    return obj


@pytest.fixture()
def client():
    mock_session = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: (yield mock_session)
    try:
        with TestClient(app) as c:
            yield c, mock_session
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_get_market_data_news_returns_filtered_articles(client):
    c, session = client
    rows = [
        _make_news(headline="MSFT item", tickers_json=["MSFT"]),
        _make_news(headline="AAPL item", tickers_json=["AAPL"]),
    ]
    session.execute.return_value.scalars.return_value.all.return_value = rows

    response = c.get("/market-data/news/AAPL")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["headline"] == "AAPL item"
    assert data[0]["tickers"] == ["AAPL"]


def test_get_market_data_news_returns_empty_list_when_none_match(client):
    c, session = client
    session.execute.return_value.scalars.return_value.all.return_value = [
        _make_news(tickers_json=["TSLA"]),
    ]

    response = c.get("/market-data/news/AAPL")

    assert response.status_code == 200
    assert response.json() == []


def test_get_auto_paper_history_returns_structured_outcome_counts(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 2 positions opened, 1 rejected, 1 gate-blocked",
                    started_at="2026-04-30T10:00:00+00:00",
                    finished_at="2026-04-30T10:00:03+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 2,
                        "rejected_count": 1,
                        "cancelled_count": 0,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                )
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["outcome_counts"] == {
        "accepted_count": 2,
        "rejected_count": 1,
        "cancelled_count": 0,
        "blocked_count": 1,
        "risk_blocked_count": 0,
        "gate_blocked_count": 1,
        "skipped_cap_count": 0,
        "legacy_broker_rejected_count": 0,
    }


def test_get_auto_paper_history_parses_legacy_message_counts(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 positions opened, 2 risk-blocked, 1 gate-blocked, 3 broker-rejected, 1 skipped (cap)",
                    started_at="2026-04-30T10:00:00+00:00",
                    finished_at="2026-04-30T10:00:03+00:00",
                    source="scheduled",
                )
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["outcome_counts"] == {
        "accepted_count": 1,
        "rejected_count": 3,
        "cancelled_count": 0,
        "blocked_count": 3,
        "risk_blocked_count": 2,
        "gate_blocked_count": 1,
        "skipped_cap_count": 1,
        "legacy_broker_rejected_count": 3,
    }


def test_trigger_auto_paper_run_persists_structured_outcome_counts(client, monkeypatch):
    c, _session = client
    recorded: list[WorkerRunEntry] = []

    class StubRunLog:
        def append(self, entry: WorkerRunEntry) -> None:
            recorded.append(entry)

    worker_result = WorkerResult(
        worker_name="auto_paper_trader",
        status="ok",
        started_at=datetime(2026, 4, 30, 10, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 4, 30, 10, 0, 5, tzinfo=timezone.utc),
        message="auto_paper_trader: 1 positions opened, 2 rejected, 1 cancelled, 1 gate-blocked",
    )

    class StubWorker:
        def run(self) -> WorkerResult:
            return worker_result

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())
    monkeypatch.setattr(market_data_route, "AutoPaperTraderWorker", lambda: StubWorker())

    response = c.post("/market-data/auto-paper/run")

    assert response.status_code == 200
    assert len(recorded) == 1
    assert recorded[0].outcome_counts == {
        "accepted_count": 1,
        "rejected_count": 2,
        "cancelled_count": 1,
        "blocked_count": 1,
        "risk_blocked_count": 0,
        "gate_blocked_count": 1,
        "skipped_cap_count": 0,
        "legacy_broker_rejected_count": 0,
    }


def test_get_auto_paper_history_filters_by_source_and_outcome(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 positions opened",
                    started_at="2026-04-30T11:00:00+00:00",
                    finished_at="2026-04-30T11:00:02+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 1,
                        "rejected_count": 0,
                        "cancelled_count": 0,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 2 rejected, 1 gate-blocked",
                    started_at="2026-04-30T10:00:00+00:00",
                    finished_at="2026-04-30T10:00:03+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 2,
                        "cancelled_count": 0,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history?source=scheduled&outcome=rejected")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["source"] == "scheduled"
    assert payload[0]["outcome_counts"]["rejected_count"] == 2


def test_get_auto_paper_history_filters_by_started_window(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 positions opened",
                    started_at="2026-04-30T12:00:00+00:00",
                    finished_at="2026-04-30T12:00:02+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 1,
                        "rejected_count": 0,
                        "cancelled_count": 0,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 cancelled",
                    started_at="2026-04-30T09:00:00+00:00",
                    finished_at="2026-04-30T09:00:02+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "cancelled_count": 1,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get(
        "/market-data/auto-paper/history?started_after=2026-04-30T10:30:00%2B00:00&started_before=2026-04-30T12:30:00%2B00:00"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["started_at"] == "2026-04-30T12:00:00+00:00"


def test_get_auto_paper_history_contract_snapshots_key_fields(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 positions opened, 1 gate-blocked",
                    started_at="2026-04-30T12:00:00+00:00",
                    finished_at="2026-04-30T12:00:02+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 1,
                        "rejected_count": 0,
                        "cancelled_count": 0,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="error",
                    message="auto_paper_trader: 2 cancelled",
                    started_at="2026-04-30T11:00:00+00:00",
                    finished_at="2026-04-30T11:00:03+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "cancelled_count": 2,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get(
        "/market-data/auto-paper/history?"
        "source=manual&outcome=blocked&"
        "started_after=2026-04-30T10:30:00%2B00:00&"
        "started_before=2026-04-30T12:30:00%2B00:00"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "worker_name": "auto_paper_trader",
            "status": "ok",
            "message": "auto_paper_trader: 1 positions opened, 1 gate-blocked",
            "started_at": "2026-04-30T12:00:00+00:00",
            "finished_at": "2026-04-30T12:00:02+00:00",
            "source": "manual",
            "outcome_counts": {
                "accepted_count": 1,
                "rejected_count": 0,
                "cancelled_count": 0,
                "blocked_count": 1,
                "risk_blocked_count": 0,
                "gate_blocked_count": 1,
                "skipped_cap_count": 0,
                "legacy_broker_rejected_count": 0,
            },
        }
    ]


def test_get_auto_paper_history_summary_returns_aggregates(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 positions opened, 1 rejected",
                    started_at="2026-04-30T12:00:00+00:00",
                    finished_at="2026-04-30T12:00:02+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 1,
                        "rejected_count": 1,
                        "cancelled_count": 0,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="error",
                    message="auto_paper_trader: 2 cancelled, 1 gate-blocked",
                    started_at="2026-04-30T10:00:00+00:00",
                    finished_at="2026-04-30T10:00:03+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "cancelled_count": 2,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "total_runs": 2,
        "manual_run_count": 1,
        "scheduled_run_count": 1,
        "success_run_count": 1,
        "error_run_count": 1,
        "accepted_total": 1,
        "rejected_total": 1,
        "cancelled_total": 2,
        "blocked_total": 1,
        "risk_blocked_total": 0,
        "gate_blocked_total": 1,
        "latest_run_started_at": "2026-04-30T12:00:00+00:00",
    }


def test_get_auto_paper_history_summary_respects_filters(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 positions opened",
                    started_at="2026-04-30T12:00:00+00:00",
                    finished_at="2026-04-30T12:00:02+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 1,
                        "rejected_count": 0,
                        "cancelled_count": 0,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 3 rejected, 1 gate-blocked",
                    started_at="2026-04-30T11:00:00+00:00",
                    finished_at="2026-04-30T11:00:03+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 3,
                        "cancelled_count": 0,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history/summary?source=scheduled&outcome=rejected")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_runs"] == 1
    assert payload["manual_run_count"] == 0
    assert payload["scheduled_run_count"] == 1
    assert payload["rejected_total"] == 3
    assert payload["blocked_total"] == 1
    assert payload["latest_run_started_at"] == "2026-04-30T11:00:00+00:00"


def test_get_auto_paper_history_summary_contract_snapshots_key_fields(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 2 positions opened",
                    started_at="2026-04-30T12:30:00+00:00",
                    finished_at="2026-04-30T12:30:04+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 2,
                        "rejected_count": 0,
                        "cancelled_count": 0,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="error",
                    message="auto_paper_trader: 1 cancelled, 1 gate-blocked",
                    started_at="2026-04-30T11:30:00+00:00",
                    finished_at="2026-04-30T11:30:03+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "cancelled_count": 1,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get(
        "/market-data/auto-paper/history/summary?"
        "source=scheduled&outcome=blocked&"
        "started_after=2026-04-30T11:00:00%2B00:00&"
        "started_before=2026-04-30T12:00:00%2B00:00"
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_runs": 1,
        "manual_run_count": 0,
        "scheduled_run_count": 1,
        "success_run_count": 0,
        "error_run_count": 1,
        "accepted_total": 0,
        "rejected_total": 0,
        "cancelled_total": 1,
        "blocked_total": 1,
        "risk_blocked_total": 0,
        "gate_blocked_total": 1,
        "latest_run_started_at": "2026-04-30T11:30:00+00:00",
    }


def test_export_auto_paper_history_returns_filtered_bundle(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 2 rejected, 1 gate-blocked",
                    started_at="2026-04-30T11:00:00+00:00",
                    finished_at="2026-04-30T11:00:03+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 2,
                        "cancelled_count": 0,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 positions opened",
                    started_at="2026-04-30T12:00:00+00:00",
                    finished_at="2026-04-30T12:00:02+00:00",
                    source="manual",
                    outcome_counts={
                        "accepted_count": 1,
                        "rejected_count": 0,
                        "cancelled_count": 0,
                        "blocked_count": 0,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 0,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                ),
            ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history/export?source=scheduled&outcome=rejected&limit=500")

    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"] == {
        "limit": 200,
        "source": "scheduled",
        "outcome": "rejected",
        "started_after": None,
        "started_before": None,
    }
    assert payload["summary"] == {
        "total_runs": 1,
        "manual_run_count": 0,
        "scheduled_run_count": 1,
        "success_run_count": 1,
        "error_run_count": 0,
        "accepted_total": 0,
        "rejected_total": 2,
        "cancelled_total": 0,
        "blocked_total": 1,
        "risk_blocked_total": 0,
        "gate_blocked_total": 1,
        "latest_run_started_at": "2026-04-30T11:00:00+00:00",
    }
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["source"] == "scheduled"
    assert payload["entries"][0]["outcome_counts"]["rejected_count"] == 2
    assert payload["exported_at"].endswith("Z") or payload["exported_at"].endswith("+00:00")


def test_export_auto_paper_history_contract_snapshots_key_fields(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 4, 30, 13, 15, 0, tzinfo=timezone.utc)

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="error",
                    message="auto_paper_trader: 1 cancelled, 1 gate-blocked",
                    started_at="2026-04-30T11:45:00+00:00",
                    finished_at="2026-04-30T11:45:05+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "cancelled_count": 1,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                )
            ]

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get(
        "/market-data/auto-paper/history/export?"
        "source=scheduled&outcome=blocked&limit=999&"
        "started_after=2026-04-30T10:00:00%2B00:00&"
        "started_before=2026-04-30T12:00:00%2B00:00"
    )

    assert response.status_code == 200
    assert response.json() == {
        "exported_at": "2026-04-30T13:15:00Z",
        "filters": {
            "limit": 200,
            "source": "scheduled",
            "outcome": "blocked",
            "started_after": "2026-04-30T10:00:00Z",
            "started_before": "2026-04-30T12:00:00Z",
        },
        "summary": {
            "total_runs": 1,
            "manual_run_count": 0,
            "scheduled_run_count": 1,
            "success_run_count": 0,
            "error_run_count": 1,
            "accepted_total": 0,
            "rejected_total": 0,
            "cancelled_total": 1,
            "blocked_total": 1,
            "risk_blocked_total": 0,
            "gate_blocked_total": 1,
            "latest_run_started_at": "2026-04-30T11:45:00+00:00",
        },
        "entries": [
            {
                "worker_name": "auto_paper_trader",
                "status": "error",
                "message": "auto_paper_trader: 1 cancelled, 1 gate-blocked",
                "started_at": "2026-04-30T11:45:00+00:00",
                "finished_at": "2026-04-30T11:45:05+00:00",
                "source": "scheduled",
                "outcome_counts": {
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "cancelled_count": 1,
                    "blocked_count": 1,
                    "risk_blocked_count": 0,
                    "gate_blocked_count": 1,
                    "skipped_cap_count": 0,
                    "legacy_broker_rejected_count": 0,
                },
            }
        ],
    }


def test_get_auto_paper_history_retention_returns_metadata(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def get_retention_metadata(self):
            return {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 73,
                "entries_remaining": 127,
                "utilization_pct": 36.5,
                "warning_threshold_pct": 80.0,
                "near_capacity": False,
                "retention_status": "ok",
                "retention_warning": None,
                "retained_span_hours": 121.86,
                "average_entries_per_day": 14.38,
                "estimated_days_until_capacity": 8.83,
                "retention_trend_status": "growing",
                "log_exists": True,
                "oldest_started_at": "2026-04-25T11:08:27.797598+00:00",
                "latest_started_at": "2026-04-30T12:00:00+00:00",
            }

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history/retention")

    assert response.status_code == 200
    assert response.json() == {
        "storage_backend": "file_jsonl",
        "trim_on_append": True,
        "max_entries": 200,
        "current_entry_count": 73,
        "entries_remaining": 127,
        "utilization_pct": 36.5,
        "warning_threshold_pct": 80.0,
        "near_capacity": False,
        "retention_status": "ok",
        "retention_warning": None,
        "retained_span_hours": 121.86,
        "average_entries_per_day": 14.38,
        "estimated_days_until_capacity": 8.83,
        "retention_trend_status": "growing",
        "log_exists": True,
        "oldest_started_at": "2026-04-25T11:08:27.797598+00:00",
        "latest_started_at": "2026-04-30T12:00:00+00:00",
    }


def test_get_auto_paper_history_retention_contract_snapshots_key_fields(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def get_retention_metadata(self):
            return {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 160,
                "entries_remaining": 40,
                "utilization_pct": 80.0,
                "warning_threshold_pct": 80.0,
                "near_capacity": True,
                "retention_status": "near_capacity",
                "retention_warning": "Auto-paper history retention is at 80.00% of the 200 entry cap.",
                "retained_span_hours": 96.0,
                "average_entries_per_day": 40.0,
                "estimated_days_until_capacity": 1.0,
                "retention_trend_status": "growing",
                "log_exists": True,
                "oldest_started_at": "2026-04-26T12:00:00+00:00",
                "latest_started_at": "2026-04-30T12:00:00+00:00",
            }

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history/retention")

    assert response.status_code == 200
    assert response.json() == {
        "storage_backend": "file_jsonl",
        "trim_on_append": True,
        "max_entries": 200,
        "current_entry_count": 160,
        "entries_remaining": 40,
        "utilization_pct": 80.0,
        "warning_threshold_pct": 80.0,
        "near_capacity": True,
        "retention_status": "near_capacity",
        "retention_warning": "Auto-paper history retention is at 80.00% of the 200 entry cap.",
        "retained_span_hours": 96.0,
        "average_entries_per_day": 40.0,
        "estimated_days_until_capacity": 1.0,
        "retention_trend_status": "growing",
        "log_exists": True,
        "oldest_started_at": "2026-04-26T12:00:00+00:00",
        "latest_started_at": "2026-04-30T12:00:00+00:00",
    }


def test_get_auto_paper_history_retention_surfaces_near_capacity_warning(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def get_retention_metadata(self):
            return {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 190,
                "entries_remaining": 10,
                "utilization_pct": 95.0,
                "warning_threshold_pct": 80.0,
                "near_capacity": True,
                "retention_status": "near_capacity",
                "retention_warning": "Auto-paper history retention is at 95.00% of the 200 entry cap.",
                "retained_span_hours": 72.0,
                "average_entries_per_day": 63.33,
                "estimated_days_until_capacity": 0.16,
                "retention_trend_status": "growing",
                "log_exists": True,
                "oldest_started_at": "2026-04-25T11:08:27.797598+00:00",
                "latest_started_at": "2026-04-30T12:00:00+00:00",
            }

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history/retention")

    assert response.status_code == 200
    payload = response.json()
    assert payload["near_capacity"] is True
    assert payload["retention_status"] == "near_capacity"
    assert payload["entries_remaining"] == 10
    assert payload["utilization_pct"] == 95.0
    assert payload["retention_warning"] == "Auto-paper history retention is at 95.00% of the 200 entry cap."
    assert payload["retained_span_hours"] == 72.0
    assert payload["average_entries_per_day"] == 63.33
    assert payload["estimated_days_until_capacity"] == 0.16
    assert payload["retention_trend_status"] == "growing"


def test_get_auto_paper_history_retention_handles_insufficient_trend_data(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def get_retention_metadata(self):
            return {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 1,
                "entries_remaining": 199,
                "utilization_pct": 0.5,
                "warning_threshold_pct": 80.0,
                "near_capacity": False,
                "retention_status": "ok",
                "retention_warning": None,
                "retained_span_hours": None,
                "average_entries_per_day": None,
                "estimated_days_until_capacity": None,
                "retention_trend_status": "insufficient_data",
                "log_exists": True,
                "oldest_started_at": "2026-04-30T12:00:00+00:00",
                "latest_started_at": "2026-04-30T12:00:00+00:00",
            }

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())

    response = c.get("/market-data/auto-paper/history/retention")

    assert response.status_code == 200
    payload = response.json()
    assert payload["retained_span_hours"] is None
    assert payload["average_entries_per_day"] is None
    assert payload["estimated_days_until_capacity"] is None
    assert payload["retention_trend_status"] == "insufficient_data"


def test_get_auto_paper_readiness_contract_snapshots_key_fields(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return [
                WorkerRunEntry(
                    worker_name="auto_paper_trader",
                    status="ok",
                    message="auto_paper_trader: 1 gate-blocked",
                    started_at="2026-04-30T12:15:00+00:00",
                    finished_at="2026-04-30T12:15:04+00:00",
                    source="scheduled",
                    outcome_counts={
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "cancelled_count": 0,
                        "blocked_count": 1,
                        "risk_blocked_count": 0,
                        "gate_blocked_count": 1,
                        "skipped_cap_count": 0,
                        "legacy_broker_rejected_count": 0,
                    },
                )
            ]

        def get_retention_metadata(self):
            return {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 48,
                "entries_remaining": 152,
                "utilization_pct": 24.0,
                "warning_threshold_pct": 80.0,
                "near_capacity": False,
                "retention_status": "ok",
                "retention_warning": None,
                "retained_span_hours": 36.0,
                "average_entries_per_day": 32.0,
                "estimated_days_until_capacity": 4.75,
                "retention_trend_status": "growing",
                "log_exists": True,
                "oldest_started_at": "2026-04-29T00:15:00+00:00",
                "latest_started_at": "2026-04-30T12:15:00+00:00",
            }

    class StubBrokerService:
        def dry_run_order(self, request, portfolio_context=None):
            _ = request
            _ = portfolio_context
            return {
                "status": "ready",
                "mode_guard_ok": True,
                "request_valid": True,
                "estimated_notional": 100.0,
                "issues": [],
                "warnings": [],
                "preflight_decision": {
                    "decision_status": "allowed",
                    "submit_gate": "not_applied",
                    "advisory_count": 0,
                    "would_block_count": 0,
                    "blocking_count": 0,
                    "advisory_items": [],
                    "would_block_items": [],
                    "blocking_items": [],
                },
                "preflight_context": None,
                "broker_mode": {
                    "broker": "ibkr",
                    "mode": "paper",
                    "live_execution_enabled": False,
                    "paper_trading_enabled": True,
                },
            }

    class StubJob:
        next_run_time = datetime(2026, 4, 30, 13, 0, 0, tzinfo=timezone.utc)

    class StubScheduler:
        def get_job(self, job_id: str):
            assert job_id == "auto_paper_trader"
            return StubJob()

    async def _fake_check_ibkr_gateway(gateway_url: str, timeout: float = 5.0) -> bool:
        assert gateway_url == "https://localhost:5000/v1/api"
        assert timeout == 5.0
        return True

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())
    monkeypatch.setattr(market_data_route, "BrokerService", StubBrokerService)
    monkeypatch.setattr(
        market_data_route,
        "get_trading_mode",
        lambda: SimpleNamespace(
            trading_mode="paper",
            execution_control="manual",
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=False,
            emergency_stop_active=False,
            reasons=(),
        ),
    )
    monkeypatch.setattr(market_data_route, "assert_mode_configuration_consistent", lambda: "paper")
    monkeypatch.setattr(
        market_data_route,
        "get_broker_mode_metadata",
        lambda: {
            "broker": "ibkr",
            "mode": "paper",
            "live_execution_enabled": False,
            "paper_trading_enabled": True,
        },
    )
    monkeypatch.setattr(market_data_route, "is_live_mode_enabled", lambda: False)
    monkeypatch.setattr(market_data_route, "is_paper_account_id", lambda account_id: account_id.startswith("DU"))
    monkeypatch.setattr(market_data_route, "check_ibkr_gateway", _fake_check_ibkr_gateway)
    monkeypatch.setattr(
        market_data_route,
        "get_settings",
        lambda: SimpleNamespace(
            ibkr_gateway_url="https://localhost:5000/v1/api",
            ibkr_account_id="DU12345",
        ),
    )
    monkeypatch.setattr(app.state, "scheduler", StubScheduler(), raising=False)

    response = c.get("/market-data/auto-paper/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "blocked",
        "ready_for_auto_submit": False,
        "blocking_reasons": ["auto_trading_disabled_by_trading_control"],
        "warning_reasons": [],
        "broker_control": {
            "trading_mode": "paper",
            "execution_control": "manual",
            "arming_state": "armed",
            "live_order_submission_allowed": False,
            "paper_order_submission_allowed": True,
            "auto_trading_allowed": False,
            "emergency_stop_active": False,
            "reasons": [],
        },
        "broker_health": {
            "status": "paper_ready",
            "mode_guard_ok": True,
            "gateway_reachable": True,
            "gateway_url": "https://localhost:5000/v1/api",
            "account_id": "DU12345",
            "account_is_paper": True,
            "broker_mode": {
                "broker": "ibkr",
                "mode": "paper",
                "live_execution_enabled": False,
                "paper_trading_enabled": True,
            },
        },
        "scheduler": {
            "job_id": "auto_paper_trader",
            "next_run_time": "2026-04-30T13:00:00Z",
            "state": "running",
        },
        "shared_paper_preflight": {
            "status": "ready",
            "mode_guard_ok": True,
            "request_valid": True,
            "estimated_notional": 100.0,
            "preflight_decision": {
                "decision_status": "allowed",
                "submit_gate": "not_applied",
                "advisory_count": 0,
                "would_block_count": 0,
                "blocking_count": 0,
                "advisory_items": [],
                "would_block_items": [],
                "blocking_items": [],
            },
            "broker_mode": {
                "broker": "ibkr",
                "mode": "paper",
                "live_execution_enabled": False,
                "paper_trading_enabled": True,
            },
        },
        "recent_history": {
            "window_limit": 20,
            "latest_run": {
                "worker_name": "auto_paper_trader",
                "status": "ok",
                "message": "auto_paper_trader: 1 gate-blocked",
                "started_at": "2026-04-30T12:15:00+00:00",
                "finished_at": "2026-04-30T12:15:04+00:00",
                "source": "scheduled",
                "outcome_counts": {
                    "accepted_count": 0,
                    "rejected_count": 0,
                    "cancelled_count": 0,
                    "blocked_count": 1,
                    "risk_blocked_count": 0,
                    "gate_blocked_count": 1,
                    "skipped_cap_count": 0,
                    "legacy_broker_rejected_count": 0,
                },
            },
            "summary": {
                "total_runs": 1,
                "manual_run_count": 0,
                "scheduled_run_count": 1,
                "success_run_count": 1,
                "error_run_count": 0,
                "accepted_total": 0,
                "rejected_total": 0,
                "cancelled_total": 0,
                "blocked_total": 1,
                "risk_blocked_total": 0,
                "gate_blocked_total": 1,
                "latest_run_started_at": "2026-04-30T12:15:00+00:00",
            },
            "retention": {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 48,
                "entries_remaining": 152,
                "utilization_pct": 24.0,
                "warning_threshold_pct": 80.0,
                "near_capacity": False,
                "retention_status": "ok",
                "retention_warning": None,
                "retained_span_hours": 36.0,
                "average_entries_per_day": 32.0,
                "estimated_days_until_capacity": 4.75,
                "retention_trend_status": "growing",
                "log_exists": True,
                "oldest_started_at": "2026-04-29T00:15:00+00:00",
                "latest_started_at": "2026-04-30T12:15:00+00:00",
            },
        },
    }


def test_get_auto_paper_readiness_surfaces_warning_posture_without_blocking_reasons(client, monkeypatch):
    c, _session = client

    class StubRunLog:
        def recent(self, limit: int = 20):
            return []

        def get_retention_metadata(self):
            return {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 0,
                "entries_remaining": 200,
                "utilization_pct": 0.0,
                "warning_threshold_pct": 80.0,
                "near_capacity": False,
                "retention_status": "ok",
                "retention_warning": None,
                "retained_span_hours": None,
                "average_entries_per_day": None,
                "estimated_days_until_capacity": None,
                "retention_trend_status": "insufficient_data",
                "log_exists": False,
                "oldest_started_at": None,
                "latest_started_at": None,
            }

    class StubBrokerService:
        def dry_run_order(self, request, portfolio_context=None):
            _ = request
            _ = portfolio_context
            return {
                "status": "ready",
                "mode_guard_ok": True,
                "request_valid": True,
                "estimated_notional": 100.0,
                "issues": [],
                "warnings": [],
                "preflight_decision": {
                    "decision_status": "would_block",
                    "submit_gate": "not_applied",
                    "advisory_count": 0,
                    "would_block_count": 1,
                    "blocking_count": 0,
                    "advisory_items": [],
                    "would_block_items": [
                        {
                            "code": "max_symbol_exposure_exceeded",
                            "message": "Would exceed symbol exposure limit",
                            "severity": "warning",
                            "source": "risk_limits",
                            "enforcement_enabled": False,
                            "classification": "would_block",
                        }
                    ],
                    "blocking_items": [],
                },
                "preflight_context": None,
                "broker_mode": {
                    "broker": "ibkr",
                    "mode": "paper",
                    "live_execution_enabled": False,
                    "paper_trading_enabled": True,
                },
            }

    class StubJob:
        next_run_time = datetime(2026, 4, 30, 13, 5, 0, tzinfo=timezone.utc)

    class StubScheduler:
        def get_job(self, job_id: str):
            assert job_id == "auto_paper_trader"
            return StubJob()

    async def _fake_check_ibkr_gateway(gateway_url: str, timeout: float = 5.0) -> bool:
        assert gateway_url == "https://localhost:5000/v1/api"
        assert timeout == 5.0
        return True

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())
    monkeypatch.setattr(market_data_route, "BrokerService", StubBrokerService)
    monkeypatch.setattr(
        market_data_route,
        "get_trading_mode",
        lambda: SimpleNamespace(
            trading_mode="paper",
            execution_control="manual",
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=True,
            emergency_stop_active=False,
            reasons=(),
        ),
    )
    monkeypatch.setattr(market_data_route, "assert_mode_configuration_consistent", lambda: "paper")
    monkeypatch.setattr(
        market_data_route,
        "get_broker_mode_metadata",
        lambda: {
            "broker": "ibkr",
            "mode": "paper",
            "live_execution_enabled": False,
            "paper_trading_enabled": True,
        },
    )
    monkeypatch.setattr(market_data_route, "is_live_mode_enabled", lambda: False)
    monkeypatch.setattr(market_data_route, "is_paper_account_id", lambda account_id: account_id.startswith("DU"))
    monkeypatch.setattr(market_data_route, "check_ibkr_gateway", _fake_check_ibkr_gateway)
    monkeypatch.setattr(
        market_data_route,
        "get_settings",
        lambda: SimpleNamespace(
            ibkr_gateway_url="https://localhost:5000/v1/api",
            ibkr_account_id="DU12345",
        ),
    )
    monkeypatch.setattr(app.state, "scheduler", StubScheduler(), raising=False)

    response = c.get("/market-data/auto-paper/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "warning"
    assert payload["ready_for_auto_submit"] is True
    assert payload["blocking_reasons"] == []
    assert payload["warning_reasons"] == [
        "shared_paper_preflight_would_block_findings",
        "history_log_not_initialized",
        "no_recent_auto_paper_history",
    ]
    assert payload["recent_history"]["latest_run"] is None
    assert payload["recent_history"]["summary"]["total_runs"] == 0
    assert payload["shared_paper_preflight"]["preflight_decision"]["would_block_count"] == 1


def _configure_auto_paper_enablement_dependencies(
    monkeypatch,
    *,
    trading_state=None,
    halt_status: TradingHaltStatusResponse | None = None,
    risk_limit_status: RiskLimitStatusResponse | None = None,
    scheduler_state: str = "running",
    run_entries: list[WorkerRunEntry] | None = None,
    retention_metadata: dict | None = None,
    dry_run_result: dict | None = None,
    initial_arming_state: str = "disarmed",
    durable_write_error: Exception | None = None,
):
    counters = {
        "dry_run_calls": 0,
        "submit_calls": 0,
        "durable_get_calls": 0,
        "durable_arm_calls": 0,
    }
    arming_events: list[dict] = []
    durable_state = {"state": initial_arming_state}

    class StubRunLog:
        def recent(self, limit: int = 20):
            _ = limit
            return run_entries or []

        def get_retention_metadata(self):
            if retention_metadata is not None:
                return retention_metadata
            return {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 1,
                "entries_remaining": 199,
                "utilization_pct": 0.5,
                "warning_threshold_pct": 80.0,
                "near_capacity": False,
                "retention_status": "ok",
                "retention_warning": None,
                "retained_span_hours": 24.0,
                "average_entries_per_day": 1.0,
                "estimated_days_until_capacity": 199.0,
                "retention_trend_status": "growing",
                "log_exists": True,
                "oldest_started_at": "2026-04-30T12:15:00+00:00",
                "latest_started_at": "2026-04-30T12:15:00+00:00",
            }

    class StubBrokerService:
        def dry_run_order(self, request, portfolio_context=None):
            _ = request
            _ = portfolio_context
            counters["dry_run_calls"] += 1
            if dry_run_result is not None:
                return dry_run_result
            return {
                "status": "ready",
                "mode_guard_ok": True,
                "request_valid": True,
                "estimated_notional": 100.0,
                "issues": [],
                "warnings": [],
                "preflight_decision": {
                    "decision_status": "allowed",
                    "submit_gate": "not_applied",
                    "advisory_count": 0,
                    "would_block_count": 0,
                    "blocking_count": 0,
                    "advisory_items": [],
                    "would_block_items": [],
                    "blocking_items": [],
                },
                "preflight_context": None,
                "broker_mode": {
                    "broker": "ibkr",
                    "mode": "paper",
                    "live_execution_enabled": False,
                    "paper_trading_enabled": True,
                },
            }

        def submit_auto_order(self, *args, **kwargs):
            _ = args
            _ = kwargs
            counters["submit_calls"] += 1
            raise AssertionError("enablement preconditions endpoint must not submit broker orders")

    class StubJob:
        next_run_time = datetime(2026, 4, 30, 13, 0, 0, tzinfo=timezone.utc)

    class StubPausedJob:
        next_run_time = None

    class StubScheduler:
        def get_job(self, job_id: str):
            assert job_id == "auto_paper_trader"
            if scheduler_state == "missing":
                return None
            if scheduler_state == "paused":
                return StubPausedJob()
            return StubJob()

    class StubTradingHaltService:
        def __init__(self, session):
            _ = session

        def get_status(self, scope: str = "global"):
            assert scope == "global"
            return halt_status or TradingHaltStatusResponse(
                emergency_stop_active=False,
                active_halt=None,
                status="clear",
                blocked_reason=None,
                enforcement_enabled=True,
                note="Active halt state is enforced in broker preflight and paper submit paths.",
            )

    class StubRiskLimitService:
        def __init__(self, session):
            _ = session

        def get_status(self, trading_mode: str | None = None):
            assert trading_mode == "paper"
            return risk_limit_status or RiskLimitStatusResponse(
                enforcement_enabled=False,
                trading_mode="paper",
                active_config=None,
                configured_limits={
                    "max_order_notional": 10000.0,
                    "daily_loss_limit_amount": 500.0,
                    "max_open_positions": 10,
                    "max_total_exposure": 50000.0,
                },
                missing_limits=[],
                has_max_order_notional=True,
                has_daily_loss_limit=True,
                has_max_open_positions=True,
                has_max_total_exposure=True,
                risk_limits_configured=True,
                note="Risk limits are configured for future enforcement but are not yet wired into broker submission.",
            )

    class StubTradingControlArmingStateService:
        def __init__(self, session):
            _ = session

        def get_effective_state(self, *, scope="auto_paper", trading_mode="paper", now=None):
            _ = (scope, trading_mode, now)
            counters["durable_get_calls"] += 1
            return durable_state["state"]

        def arm_state(self, **kwargs):
            counters["durable_arm_calls"] += 1
            if durable_write_error is not None:
                raise durable_write_error
            durable_state["state"] = "armed"
            return SimpleNamespace(state="armed", **kwargs)

    async def _fake_check_ibkr_gateway(gateway_url: str, timeout: float = 5.0) -> bool:
        assert gateway_url == "https://localhost:5000/v1/api"
        assert timeout == 5.0
        return True

    if trading_state is None:
        trading_state = SimpleNamespace(
            trading_mode="paper",
            execution_control="manual",
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=True,
            emergency_stop_active=False,
            reasons=(),
        )

    if run_entries is None:
        run_entries = [
            WorkerRunEntry(
                worker_name="auto_paper_trader",
                status="ok",
                message="auto_paper_trader: 1 accepted",
                started_at="2026-04-30T12:15:00+00:00",
                finished_at="2026-04-30T12:15:04+00:00",
                source="scheduled",
                outcome_counts={
                    "accepted_count": 1,
                    "rejected_count": 0,
                    "cancelled_count": 0,
                    "blocked_count": 0,
                    "risk_blocked_count": 0,
                    "gate_blocked_count": 0,
                    "skipped_cap_count": 0,
                    "legacy_broker_rejected_count": 0,
                },
            )
        ]

    monkeypatch.setattr(market_data_route, "_run_log", StubRunLog())
    monkeypatch.setattr(market_data_route, "BrokerService", StubBrokerService)
    monkeypatch.setattr(market_data_route, "TradingHaltService", StubTradingHaltService)
    monkeypatch.setattr(market_data_route, "RiskLimitService", StubRiskLimitService)
    monkeypatch.setattr(market_data_route, "TradingControlArmingStateService", StubTradingControlArmingStateService)
    monkeypatch.setattr(market_data_route, "get_trading_mode", lambda: trading_state)
    monkeypatch.setattr(market_data_route, "assert_mode_configuration_consistent", lambda: "paper")
    monkeypatch.setattr(
        market_data_route,
        "get_broker_mode_metadata",
        lambda: {
            "broker": "ibkr",
            "mode": "paper",
            "live_execution_enabled": False,
            "paper_trading_enabled": True,
        },
    )
    monkeypatch.setattr(market_data_route, "is_live_mode_enabled", lambda: False)
    monkeypatch.setattr(market_data_route, "is_paper_account_id", lambda account_id: account_id.startswith("DU"))
    monkeypatch.setattr(market_data_route, "check_ibkr_gateway", _fake_check_ibkr_gateway)
    monkeypatch.setattr(
        market_data_route,
        "get_settings",
        lambda: SimpleNamespace(
            ibkr_gateway_url="https://localhost:5000/v1/api",
            ibkr_account_id="DU12345",
        ),
    )

    if scheduler_state == "scheduler_unavailable":
        monkeypatch.setattr(app.state, "scheduler", None, raising=False)
    else:
        monkeypatch.setattr(app.state, "scheduler", StubScheduler(), raising=False)

    if initial_arming_state == "armed":
        arming_events.append(
            {
                "event": "auto_paper_arming_action",
                "action": "arm",
                "result_status": "armed",
                "arming_state_after": "armed",
                "ts": "2026-05-01T14:00:00+00:00",
            }
        )

    def _log_auto_paper_arming_action(**event):
        event.setdefault("event", "auto_paper_arming_action")
        event.setdefault("ts", "2026-05-01T14:00:00+00:00")
        arming_events.append(event)

    def _get_latest_auto_paper_arming_action():
        return arming_events[-1] if arming_events else None

    monkeypatch.setattr(market_data_route.audit_log_service, "log_auto_paper_arming_action", _log_auto_paper_arming_action)
    monkeypatch.setattr(
        market_data_route.audit_log_service,
        "get_latest_auto_paper_arming_action",
        _get_latest_auto_paper_arming_action,
    )

    return counters, arming_events


def _build_auto_paper_arming_request_from_snapshot(snapshot: dict, **overrides) -> dict:
    payload = {
        "requested_by": "operator@example.com",
        "reason": "Paper auto arming review approved",
        "expected_enablement_checked_at": snapshot["checked_at"],
        "expected_enablement_status": "ready",
        "expected_blockers": snapshot["blockers"],
        "expected_warnings": snapshot["warnings"],
        "acknowledged_warning_codes": [],
        "client_request_id": "arm-req-001",
    }
    payload.update(overrides)
    return payload


def test_get_auto_paper_enablement_preconditions_defaults_to_enableable_false(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_enablement_dependencies(
        monkeypatch,
        trading_state=SimpleNamespace(
            trading_mode="paper",
            execution_control="manual",
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=False,
            emergency_stop_active=False,
            reasons=(),
        ),
    )

    response = c.get("/market-data/auto-paper/enablement-preconditions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enableable"] is False
    assert payload["status"] == "blocked"
    assert "auto_trading_disabled_by_trading_control" in payload["blockers"]
    assert "auto_trading_control_allows_enablement" in payload["missing_checks"]


def test_get_auto_paper_enablement_preconditions_contract_snapshots_key_fields(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return cls(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    _configure_auto_paper_enablement_dependencies(
        monkeypatch,
        trading_state=SimpleNamespace(
            trading_mode="paper",
            execution_control="manual",
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=False,
            emergency_stop_active=False,
            reasons=(),
        ),
    )

    response = c.get("/market-data/auto-paper/enablement-preconditions")

    assert response.status_code == 200
    assert response.json() == {
        "status": "blocked",
        "enableable": False,
        "blockers": ["auto_trading_disabled_by_trading_control"],
        "warnings": [],
        "satisfied_checks": [
            "paper_mode_configured",
            "paper_order_submission_available",
            "live_trading_disabled",
            "broker_mode_guard_consistent",
            "broker_gateway_reachable",
            "paper_account_configured",
            "trading_halt_clear",
            "risk_limits_configured",
            "risk_limit_coverage_complete",
            "auto_paper_scheduler_running",
            "shared_paper_preflight_clear",
            "history_retention_has_headroom",
            "history_log_initialized",
            "recent_auto_paper_history_present",
        ],
        "missing_checks": ["auto_trading_control_allows_enablement"],
        "supporting_routes": {
            "readiness": "/market-data/auto-paper/readiness",
            "broker_control": "/broker/control",
            "broker_health": "/broker/health",
            "trading_halt": "/trading/halt/status?scope=global",
            "risk_limits": "/risk/limits/status?trading_mode=paper",
            "shared_paper_preflight": "/broker/orders/dry-run",
            "scheduler": "/market-data/auto-paper/scheduler/status",
            "history": "/market-data/auto-paper/history",
            "history_summary": "/market-data/auto-paper/history/summary",
            "history_retention": "/market-data/auto-paper/history/retention",
            "history_export": "/market-data/auto-paper/history/export",
        },
        "checked_at": "2026-05-01T14:00:00Z",
        "broker_control": {
            "trading_mode": "paper",
            "execution_control": "manual",
            "arming_state": "armed",
            "live_order_submission_allowed": False,
            "paper_order_submission_allowed": True,
            "auto_trading_allowed": False,
            "emergency_stop_active": False,
            "reasons": [],
        },
        "broker_health": {
            "status": "paper_ready",
            "mode_guard_ok": True,
            "gateway_reachable": True,
            "gateway_url": "https://localhost:5000/v1/api",
            "account_id": "DU12345",
            "account_is_paper": True,
            "broker_mode": {
                "broker": "ibkr",
                "mode": "paper",
                "live_execution_enabled": False,
                "paper_trading_enabled": True,
            },
        },
        "trading_halt": {
            "emergency_stop_active": False,
            "active_halt": None,
            "status": "clear",
            "blocked_reason": None,
            "enforcement_enabled": True,
            "note": "Active halt state is enforced in broker preflight and paper submit paths.",
        },
        "risk_limits": {
            "enforcement_enabled": False,
            "trading_mode": "paper",
            "active_config": None,
            "configured_limits": {
                "max_order_notional": 10000.0,
                "daily_loss_limit_amount": 500.0,
                "max_open_positions": 10,
                "max_total_exposure": 50000.0,
            },
            "missing_limits": [],
            "has_max_order_notional": True,
            "has_daily_loss_limit": True,
            "has_max_open_positions": True,
            "has_max_total_exposure": True,
            "risk_limits_configured": True,
            "note": "Risk limits are configured for future enforcement but are not yet wired into broker submission.",
        },
        "scheduler": {
            "job_id": "auto_paper_trader",
            "next_run_time": "2026-04-30T13:00:00Z",
            "state": "running",
        },
        "shared_paper_preflight": {
            "status": "ready",
            "mode_guard_ok": True,
            "request_valid": True,
            "estimated_notional": 100.0,
            "preflight_decision": {
                "decision_status": "allowed",
                "submit_gate": "not_applied",
                "advisory_count": 0,
                "would_block_count": 0,
                "blocking_count": 0,
                "advisory_items": [],
                "would_block_items": [],
                "blocking_items": [],
            },
            "broker_mode": {
                "broker": "ibkr",
                "mode": "paper",
                "live_execution_enabled": False,
                "paper_trading_enabled": True,
            },
        },
        "recent_history": {
            "window_limit": 20,
            "latest_run": {
                "worker_name": "auto_paper_trader",
                "status": "ok",
                "message": "auto_paper_trader: 1 accepted",
                "started_at": "2026-04-30T12:15:00+00:00",
                "finished_at": "2026-04-30T12:15:04+00:00",
                "source": "scheduled",
                "outcome_counts": {
                    "accepted_count": 1,
                    "rejected_count": 0,
                    "cancelled_count": 0,
                    "blocked_count": 0,
                    "risk_blocked_count": 0,
                    "gate_blocked_count": 0,
                    "skipped_cap_count": 0,
                    "legacy_broker_rejected_count": 0,
                },
            },
            "summary": {
                "total_runs": 1,
                "manual_run_count": 0,
                "scheduled_run_count": 1,
                "success_run_count": 1,
                "error_run_count": 0,
                "accepted_total": 1,
                "rejected_total": 0,
                "cancelled_total": 0,
                "blocked_total": 0,
                "risk_blocked_total": 0,
                "gate_blocked_total": 0,
                "latest_run_started_at": "2026-04-30T12:15:00+00:00",
            },
            "retention": {
                "storage_backend": "file_jsonl",
                "trim_on_append": True,
                "max_entries": 200,
                "current_entry_count": 1,
                "entries_remaining": 199,
                "utilization_pct": 0.5,
                "warning_threshold_pct": 80.0,
                "near_capacity": False,
                "retention_status": "ok",
                "retention_warning": None,
                "retained_span_hours": 24.0,
                "average_entries_per_day": 1.0,
                "estimated_days_until_capacity": 199.0,
                "retention_trend_status": "growing",
                "log_exists": True,
                "oldest_started_at": "2026-04-30T12:15:00+00:00",
                "latest_started_at": "2026-04-30T12:15:00+00:00",
            },
        },
    }


def test_get_auto_paper_enablement_preconditions_surfaces_active_halt_as_blocker(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_enablement_dependencies(
        monkeypatch,
        halt_status=TradingHaltStatusResponse(
            emergency_stop_active=True,
            active_halt=None,
            status="active",
            blocked_reason="Trading halt active (manual) for scope 'global': Operator stop",
            enforcement_enabled=True,
            note="Active halt state is enforced in broker preflight and paper submit paths.",
        ),
    )

    response = c.get("/market-data/auto-paper/enablement-preconditions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enableable"] is False
    assert "active_trading_halt" in payload["blockers"]
    assert payload["trading_halt"]["status"] == "active"


def test_get_auto_paper_enablement_preconditions_surfaces_missing_risk_limits(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_enablement_dependencies(
        monkeypatch,
        risk_limit_status=RiskLimitStatusResponse(
            enforcement_enabled=False,
            trading_mode="paper",
            active_config=None,
            configured_limits={},
            missing_limits=[
                "max_order_notional",
                "daily_loss_limit_amount",
                "max_open_positions",
                "max_total_exposure",
            ],
            has_max_order_notional=False,
            has_daily_loss_limit=False,
            has_max_open_positions=False,
            has_max_total_exposure=False,
            risk_limits_configured=False,
            note="Risk limits are configured for future enforcement but are not yet wired into broker submission.",
        ),
    )

    response = c.get("/market-data/auto-paper/enablement-preconditions")

    assert response.status_code == 200
    payload = response.json()
    assert "risk_limits_not_configured" in payload["warnings"]
    assert "risk_limits_configured" in payload["missing_checks"]
    assert payload["risk_limits"]["risk_limits_configured"] is False


def test_get_auto_paper_enablement_preconditions_surfaces_scheduler_disabled(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_enablement_dependencies(monkeypatch, scheduler_state="paused")

    response = c.get("/market-data/auto-paper/enablement-preconditions")

    assert response.status_code == 200
    payload = response.json()
    assert "auto_paper_scheduler_paused" in payload["warnings"]
    assert "auto_paper_scheduler_running" in payload["missing_checks"]
    assert payload["scheduler"]["state"] == "paused"


def test_get_auto_paper_enablement_preconditions_lists_supporting_routes(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_enablement_dependencies(monkeypatch)

    response = c.get("/market-data/auto-paper/enablement-preconditions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["supporting_routes"] == {
        "readiness": "/market-data/auto-paper/readiness",
        "broker_control": "/broker/control",
        "broker_health": "/broker/health",
        "trading_halt": "/trading/halt/status?scope=global",
        "risk_limits": "/risk/limits/status?trading_mode=paper",
        "shared_paper_preflight": "/broker/orders/dry-run",
        "scheduler": "/market-data/auto-paper/scheduler/status",
        "history": "/market-data/auto-paper/history",
        "history_summary": "/market-data/auto-paper/history/summary",
        "history_retention": "/market-data/auto-paper/history/retention",
        "history_export": "/market-data/auto-paper/history/export",
    }


def test_get_auto_paper_enablement_preconditions_is_read_only(client, monkeypatch):
    c, _session = client
    counters, _arming_events = _configure_auto_paper_enablement_dependencies(monkeypatch)

    response = c.get("/market-data/auto-paper/enablement-preconditions")

    assert response.status_code == 200
    assert counters["dry_run_calls"] == 1
    assert counters["submit_calls"] == 0


def test_post_auto_paper_arming_arms_when_enablement_snapshot_is_ready(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return cls(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    counters, arming_events = _configure_auto_paper_enablement_dependencies(monkeypatch)

    snapshot_response = c.get("/market-data/auto-paper/enablement-preconditions")
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    assert snapshot["status"] == "ready"
    assert snapshot["enableable"] is True

    response = c.post(
        "/market-data/auto-paper/arming",
        json=_build_auto_paper_arming_request_from_snapshot(snapshot),
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "warning_codes",
        "enablement_snapshot",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }
    assert payload["status"] == "armed"
    assert payload["arming_state"] == "armed"
    assert payload["failure_reasons"] == []
    assert payload["warning_codes"] == []
    assert payload["audit_recorded"] is True
    assert payload["audit_event_type"] == "auto_paper_arming_action"
    assert payload["requested_by"] == "operator@example.com"
    assert payload["reason"] == "Paper auto arming review approved"
    assert payload["client_request_id"] == "arm-req-001"
    assert payload["enablement_snapshot"]["status"] == "ready"
    assert counters["submit_calls"] == 0
    assert counters["durable_get_calls"] == 1
    assert counters["durable_arm_calls"] == 1
    assert len(arming_events) == 1
    assert set(arming_events[0]) == {
        "event",
        "action",
        "requested_by",
        "reason",
        "result_status",
        "client_request_id",
        "failure_reasons",
        "warning_codes",
        "enablement_checked_at",
        "enablement_status",
        "enablement_blockers",
        "enablement_warnings",
        "trading_mode",
        "execution_control",
        "arming_state_before",
        "arming_state_after",
        "extra",
        "ts",
    }
    assert arming_events[0]["action"] == "arm"
    assert arming_events[0]["requested_by"] == "operator@example.com"
    assert arming_events[0]["reason"] == "Paper auto arming review approved"
    assert arming_events[0]["result_status"] == "armed"
    assert arming_events[0]["client_request_id"] == "arm-req-001"
    assert arming_events[0]["failure_reasons"] == []
    assert arming_events[0]["warning_codes"] == []
    assert arming_events[0]["enablement_status"] == "ready"
    assert arming_events[0]["enablement_blockers"] == []
    assert arming_events[0]["enablement_warnings"] == []
    assert arming_events[0]["trading_mode"] == "paper"
    assert arming_events[0]["execution_control"] == "manual"
    assert arming_events[0]["arming_state_before"] == "disarmed"
    assert arming_events[0]["arming_state_after"] == "armed"
    assert arming_events[0]["extra"] == {"acknowledged_warning_codes": []}


def test_post_auto_paper_arming_rejects_when_enablement_not_ready(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return cls(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    counters, arming_events = _configure_auto_paper_enablement_dependencies(
        monkeypatch,
        trading_state=SimpleNamespace(
            trading_mode="paper",
            execution_control="manual",
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=False,
            emergency_stop_active=False,
            reasons=(),
        ),
    )

    blocked_snapshot = c.get("/market-data/auto-paper/enablement-preconditions").json()

    response = c.post(
        "/market-data/auto-paper/arming",
        json=_build_auto_paper_arming_request_from_snapshot(
            blocked_snapshot,
            expected_enablement_status="ready",
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert payload["arming_state"] == "disarmed"
    assert "enablement_preconditions_not_ready" in payload["failure_reasons"]
    assert "auto_trading_still_disabled" in payload["failure_reasons"]
    assert counters["submit_calls"] == 0
    assert counters["durable_arm_calls"] == 0
    assert len(arming_events) == 1
    assert arming_events[0]["result_status"] == "rejected"


def test_post_auto_paper_arming_rejects_stale_snapshot(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return cls(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    _counters, arming_events = _configure_auto_paper_enablement_dependencies(monkeypatch)

    ready_snapshot = c.get("/market-data/auto-paper/enablement-preconditions").json()
    stale_request = _build_auto_paper_arming_request_from_snapshot(
        ready_snapshot,
        expected_enablement_checked_at="2026-05-01T13:40:00Z",
    )

    response = c.post("/market-data/auto-paper/arming", json=stale_request)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "enablement_snapshot_stale" in payload["failure_reasons"]
    assert _counters["durable_arm_calls"] == 0
    assert len(arming_events) == 1
    assert arming_events[0]["result_status"] == "rejected"


def test_post_auto_paper_arming_rejects_when_already_armed(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return cls(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    _counters, _arming_events = _configure_auto_paper_enablement_dependencies(
        monkeypatch,
        initial_arming_state="armed",
    )

    ready_snapshot = c.get("/market-data/auto-paper/enablement-preconditions").json()

    response = c.post(
        "/market-data/auto-paper/arming",
        json=_build_auto_paper_arming_request_from_snapshot(ready_snapshot),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert payload["arming_state"] == "armed"
    assert "auto_paper_already_armed" in payload["failure_reasons"]
    assert _counters["durable_arm_calls"] == 0


def test_post_auto_paper_arming_does_not_submit_broker_orders(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return cls(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    counters, _arming_events = _configure_auto_paper_enablement_dependencies(monkeypatch)

    ready_snapshot = c.get("/market-data/auto-paper/enablement-preconditions").json()
    response = c.post(
        "/market-data/auto-paper/arming",
        json=_build_auto_paper_arming_request_from_snapshot(ready_snapshot),
    )

    assert response.status_code == 200
    assert counters["submit_calls"] == 0


def test_post_auto_paper_arming_fails_closed_when_durable_write_fails(client, monkeypatch):
    c, _session = client

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            _ = tz
            return cls(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(market_data_route, "datetime", FrozenDateTime)
    counters, arming_events = _configure_auto_paper_enablement_dependencies(
        monkeypatch,
        durable_write_error=RuntimeError("db unavailable"),
    )

    ready_snapshot = c.get("/market-data/auto-paper/enablement-preconditions").json()
    response = c.post(
        "/market-data/auto-paper/arming",
        json=_build_auto_paper_arming_request_from_snapshot(ready_snapshot),
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "warning_codes",
        "enablement_snapshot",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }
    assert payload["status"] == "rejected"
    assert payload["arming_state"] == "disarmed"
    assert "durable_arming_state_write_failed" in payload["failure_reasons"]
    assert payload["audit_recorded"] is True
    assert payload["audit_event_type"] == "auto_paper_arming_action"
    assert payload["requested_by"] == "operator@example.com"
    assert payload["reason"] == "Paper auto arming review approved"
    assert payload["client_request_id"] == "arm-req-001"
    assert counters["submit_calls"] == 0
    assert counters["durable_arm_calls"] == 1
    assert len(arming_events) == 1
    assert set(arming_events[0]) == {
        "event",
        "action",
        "requested_by",
        "reason",
        "result_status",
        "client_request_id",
        "failure_reasons",
        "warning_codes",
        "enablement_checked_at",
        "enablement_status",
        "enablement_blockers",
        "enablement_warnings",
        "trading_mode",
        "execution_control",
        "arming_state_before",
        "arming_state_after",
        "extra",
        "ts",
    }
    assert arming_events[0]["action"] == "arm"
    assert arming_events[0]["requested_by"] == "operator@example.com"
    assert arming_events[0]["reason"] == "Paper auto arming review approved"
    assert arming_events[0]["result_status"] == "rejected"
    assert arming_events[0]["client_request_id"] == "arm-req-001"
    assert "durable_arming_state_write_failed" in arming_events[0]["failure_reasons"]
    assert arming_events[0]["warning_codes"] == []
    assert arming_events[0]["enablement_status"] == "ready"
    assert arming_events[0]["enablement_blockers"] == []
    assert arming_events[0]["enablement_warnings"] == []
    assert arming_events[0]["trading_mode"] == "paper"
    assert arming_events[0]["execution_control"] == "manual"
    assert arming_events[0]["arming_state_before"] == "disarmed"
    assert arming_events[0]["arming_state_after"] == "disarmed"
    assert arming_events[0]["extra"] == {"acknowledged_warning_codes": []}


def test_auto_paper_arming_failure_code_vocab_is_locked():
    assert market_data_route._AUTO_PAPER_ARMING_FAILURE_CODE_DESCRIPTIONS == {
        "enablement_preconditions_not_ready": "The recomputed enablement-preconditions contract is not ready for arming.",
        "enablement_snapshot_stale": "The operator-supplied enablement snapshot is stale or no longer matches current backend posture.",
        "auto_paper_already_armed": "The auto-paper arming surface is already in the armed state.",
        "durable_arming_state_write_failed": "The durable arming-state write failed, so the arming mutation was rejected fail-closed.",
        "auto_trading_still_disabled": "Trading control still reports auto trading as disabled.",
        "trading_mode_not_paper": "Trading mode is not paper.",
        "live_trading_not_disabled": "Live trading is not fully disabled.",
        "active_trading_halt": "A global trading halt is active.",
        "shared_preflight_not_clear": "The shared paper preflight seam is not clear.",
        "operator_reason_required": "A non-empty arming reason is required.",
        "requested_by_required": "A non-empty requested_by value is required.",
    }


def test_auto_paper_enablement_preconditions_code_vocab_is_locked():
    assert market_data_route._AUTO_PAPER_ENABLEMENT_BLOCKER_CODE_DESCRIPTIONS == {
        "trading_mode_not_paper": "Paper trading mode is not configured for the current broker control state.",
        "paper_order_submission_disabled": "Paper order submission is not currently allowed by trading control.",
        "auto_trading_disabled_by_trading_control": "Auto trading remains disabled by the trading control guard.",
        "live_trading_enabled": "Live trading is still enabled and must remain blocked for paper-auto pre-enable review.",
        "broker_mode_misconfigured": "Broker mode guard configuration is inconsistent.",
        "broker_gateway_unreachable": "Broker gateway reachability is not healthy enough for enablement review.",
        "ibkr_account_not_paper": "Configured IBKR account does not look like a paper account.",
        "active_trading_halt": "An active trading halt is still in force.",
        "shared_paper_preflight_blocking_findings": "The shared paper preflight seam is already returning blocking findings.",
    }
    assert market_data_route._AUTO_PAPER_ENABLEMENT_WARNING_CODE_DESCRIPTIONS == {
        "risk_limits_not_configured": "No paper risk-limit configuration is currently present.",
        "risk_limit_coverage_incomplete": "Risk-limit configuration exists but does not cover the full expected paper checklist.",
        "auto_paper_scheduler_paused": "The auto-paper scheduler exists but is currently paused.",
        "auto_paper_scheduler_missing": "The auto-paper scheduler job is not currently registered.",
        "auto_paper_scheduler_scheduler_unavailable": "The scheduler runtime is not currently available.",
        "shared_paper_preflight_would_block_findings": "The shared paper preflight seam shows would-block findings that still need review.",
        "shared_paper_preflight_advisory_findings": "The shared paper preflight seam shows advisory findings that still need review.",
        "history_retention_near_capacity": "The retained auto-paper history window is nearing capacity.",
        "history_log_not_initialized": "The retained auto-paper history log has not been initialized yet.",
        "no_recent_auto_paper_history": "There is no recent retained auto-paper run history yet.",
    }
    assert market_data_route._AUTO_PAPER_ENABLEMENT_CHECK_CODE_DESCRIPTIONS == {
        "paper_mode_configured": "Broker control is configured for paper trading mode.",
        "paper_order_submission_available": "Paper order submission is currently allowed by trading control.",
        "auto_trading_control_allows_enablement": "Trading control would allow auto trading if all other prerequisites were satisfied.",
        "live_trading_disabled": "Live trading remains disabled.",
        "broker_mode_guard_consistent": "Broker mode guard configuration is internally consistent.",
        "broker_gateway_reachable": "The configured broker gateway is reachable.",
        "paper_account_configured": "The configured IBKR account looks like a paper account.",
        "trading_halt_clear": "No active global trading halt is present.",
        "risk_limits_configured": "At least one active paper risk-limit configuration is present.",
        "risk_limit_coverage_complete": "The current paper risk-limit configuration covers the expected checklist fields.",
        "auto_paper_scheduler_running": "The auto-paper scheduler job is present and running.",
        "shared_paper_preflight_clear": "The shared paper preflight seam currently reports no blocking or advisory findings.",
        "history_retention_has_headroom": "The retained auto-paper history window still has capacity headroom.",
        "history_log_initialized": "The retained auto-paper history log exists.",
        "recent_auto_paper_history_present": "There is recent retained auto-paper run history to inspect.",
    }


# ---------------------------------------------------------------------------
# GET /market-data/auto-paper/arming  (MH-134 readback endpoint)
# ---------------------------------------------------------------------------


def _configure_auto_paper_readback_dependencies(monkeypatch, *, posture):
    """Minimal stub for the GET /auto-paper/arming readback endpoint.

    Only wires TradingControlArmingStateService.get_readback_posture so the
    route handler can stay thin.  No broker, scheduler, or enablement stubs are
    needed because the readback endpoint does not touch those surfaces.
    """

    class StubReadbackService:
        def __init__(self, session):
            _ = session

        def get_readback_posture(self, *, scope="auto_paper", trading_mode="paper", now=None):
            _ = (scope, trading_mode, now)
            return posture

    monkeypatch.setattr(market_data_route, "TradingControlArmingStateService", StubReadbackService)


def _build_readback_posture_stub(
    *,
    status="armed",
    arming_state="armed",
    scope="auto_paper",
    trading_mode="paper",
    fail_closed_reason=None,
    durable_row_present=True,
    duplicate_rows_detected=False,
    stored_state="armed",
    armed_at=None,
    armed_by="ops@example.com",
    arm_reason="Approved by ops",
    expires_at=None,
    expired=False,
    last_enablement_checked_at=None,
    last_enablement_status="ready",
    last_enablement_blockers=None,
    last_enablement_warnings=None,
    client_request_id="arm-req-001",
    disarmed_at=None,
    disarmed_by=None,
    disarm_reason=None,
    last_audit=None,
):
    return SimpleNamespace(
        status=status,
        arming_state=arming_state,
        scope=scope,
        trading_mode=trading_mode,
        evaluated_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
        fail_closed_reason=fail_closed_reason,
        durable_row_present=durable_row_present,
        duplicate_rows_detected=duplicate_rows_detected,
        stored_state=stored_state,
        armed_at=armed_at or datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        armed_by=armed_by,
        arm_reason=arm_reason,
        expires_at=expires_at,
        expired=expired,
        last_enablement_checked_at=last_enablement_checked_at,
        last_enablement_status=last_enablement_status,
        last_enablement_blockers=last_enablement_blockers or [],
        last_enablement_warnings=last_enablement_warnings or [],
        client_request_id=client_request_id,
        disarmed_at=disarmed_at,
        disarmed_by=disarmed_by,
        disarm_reason=disarm_reason,
        last_audit=last_audit,
    )


def test_get_auto_paper_arming_returns_armed_posture(client, monkeypatch):
    c, _session = client
    posture = _build_readback_posture_stub(status="armed", arming_state="armed")
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "armed"
    assert payload["arming_state"] == "armed"
    assert payload["scope"] == "auto_paper"
    assert payload["trading_mode"] == "paper"
    assert payload["fail_closed_reason"] is None
    assert payload["durable_row_present"] is True
    assert payload["duplicate_rows_detected"] is False
    assert payload["stored_state"] == "armed"
    assert payload["armed_by"] == "ops@example.com"
    assert payload["arm_reason"] == "Approved by ops"
    assert payload["expired"] is False
    assert payload["last_audit"] is None


def test_get_auto_paper_arming_returns_disarmed_posture(client, monkeypatch):
    c, _session = client
    posture = _build_readback_posture_stub(
        status="disarmed",
        arming_state="disarmed",
        stored_state="disarmed",
        armed_at=None,
        armed_by=None,
        arm_reason=None,
        disarmed_by="ops@example.com",
        disarm_reason="Intentional reset",
    )
    posture.armed_at = None
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "disarmed"
    assert payload["arming_state"] == "disarmed"
    assert payload["fail_closed_reason"] is None
    assert payload["disarmed_by"] == "ops@example.com"
    assert payload["disarm_reason"] == "Intentional reset"


def test_get_auto_paper_arming_returns_fail_closed_posture(client, monkeypatch):
    c, _session = client
    posture = _build_readback_posture_stub(
        status="fail_closed",
        arming_state="disarmed",
        stored_state=None,
        fail_closed_reason="durable_state_missing",
        durable_row_present=False,
    )
    posture.armed_at = None
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail_closed"
    assert payload["arming_state"] == "disarmed"
    assert payload["fail_closed_reason"] == "durable_state_missing"
    assert payload["durable_row_present"] is False


def test_get_auto_paper_arming_includes_last_audit_when_present(client, monkeypatch):
    c, _session = client
    audit = SimpleNamespace(
        event_type="auto_paper_arming_action",
        recorded_at=datetime(2026, 5, 1, 13, 0, 0, tzinfo=timezone.utc),
        action="arm",
        result_status="armed",
        requested_by="ops@example.com",
        reason="Approved",
        client_request_id="arm-req-001",
        arming_state_before="disarmed",
        arming_state_after="armed",
        failure_reasons=[],
        warning_codes=[],
    )
    posture = _build_readback_posture_stub(last_audit=audit)
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_audit"] is not None
    assert payload["last_audit"]["event_type"] == "auto_paper_arming_action"
    assert payload["last_audit"]["action"] == "arm"
    assert payload["last_audit"]["result_status"] == "armed"
    assert payload["last_audit"]["requested_by"] == "ops@example.com"
    assert payload["last_audit"]["arming_state_before"] == "disarmed"
    assert payload["last_audit"]["arming_state_after"] == "armed"
    assert payload["last_audit"]["failure_reasons"] == []
    assert payload["last_audit"]["warning_codes"] == []


def test_get_auto_paper_arming_response_top_level_field_set_is_locked(client, monkeypatch):
    c, _session = client
    posture = _build_readback_posture_stub()
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "status",
        "arming_state",
        "scope",
        "trading_mode",
        "evaluated_at",
        "fail_closed_reason",
        "durable_row_present",
        "duplicate_rows_detected",
        "stored_state",
        "armed_at",
        "armed_by",
        "arm_reason",
        "expires_at",
        "expired",
        "last_enablement_checked_at",
        "last_enablement_status",
        "last_enablement_blockers",
        "last_enablement_warnings",
        "client_request_id",
        "disarmed_at",
        "disarmed_by",
        "disarm_reason",
        "last_audit",
    }


def test_get_auto_paper_arming_is_read_only(client, monkeypatch):
    """GET /auto-paper/arming must not call arm_state, disarm_state, or any broker submit path."""
    c, _session = client
    mutations: list[str] = []

    class StubReadbackServiceWithMutationCheck:
        def __init__(self, session):
            _ = session

        def get_readback_posture(self, *, scope="auto_paper", trading_mode="paper", now=None):
            _ = (scope, trading_mode, now)
            return _build_readback_posture_stub()

        def arm_state(self, **kwargs):
            mutations.append("arm_state")

        def disarm_state(self, **kwargs):
            mutations.append("disarm_state")

    monkeypatch.setattr(market_data_route, "TradingControlArmingStateService", StubReadbackServiceWithMutationCheck)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    assert mutations == [], f"Read-only GET must not call: {mutations}"


# ---------------------------------------------------------------------------
# MH-135 — Auto Paper Arming Readback Endpoint Contract Review
# Contract-lock tests: Pydantic model field sets, status vocabulary,
# full per-posture snapshots, last_audit boundary.
# ---------------------------------------------------------------------------


def test_auto_paper_arming_readback_response_pydantic_field_set_is_locked():
    """Pin AutoPaperArmingReadbackResponse field names so accidental additions/removals are caught."""
    assert set(market_data_route.AutoPaperArmingReadbackResponse.model_fields.keys()) == {
        "status",
        "arming_state",
        "scope",
        "trading_mode",
        "evaluated_at",
        "fail_closed_reason",
        "durable_row_present",
        "duplicate_rows_detected",
        "stored_state",
        "armed_at",
        "armed_by",
        "arm_reason",
        "expires_at",
        "expired",
        "last_enablement_checked_at",
        "last_enablement_status",
        "last_enablement_blockers",
        "last_enablement_warnings",
        "client_request_id",
        "disarmed_at",
        "disarmed_by",
        "disarm_reason",
        "last_audit",
    }


def test_auto_paper_arming_audit_summary_response_pydantic_field_set_is_locked():
    """Pin AutoPaperArmingAuditSummaryResponse field names so the safe audit boundary cannot silently drift."""
    assert set(market_data_route.AutoPaperArmingAuditSummaryResponse.model_fields.keys()) == {
        "event_type",
        "recorded_at",
        "action",
        "result_status",
        "requested_by",
        "reason",
        "client_request_id",
        "arming_state_before",
        "arming_state_after",
        "failure_reasons",
        "warning_codes",
    }


def test_get_auto_paper_arming_status_vocabulary_is_locked(client, monkeypatch):
    """All three status values must return HTTP 200 and appear verbatim in the response payload."""
    c, _session = client
    for status_value, arming_value, fail_reason in [
        ("armed", "armed", None),
        ("disarmed", "disarmed", None),
        ("fail_closed", "disarmed", "durable_state_expired"),
    ]:
        posture = _build_readback_posture_stub(
            status=status_value,
            arming_state=arming_value,
            fail_closed_reason=fail_reason,
        )
        _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)
        response = c.get("/market-data/auto-paper/arming")
        assert response.status_code == 200, f"Expected 200 for status={status_value!r}"
        assert response.json()["status"] == status_value


def test_get_auto_paper_arming_last_audit_json_field_set_is_locked(client, monkeypatch):
    """Pin the exact key set that appears in the last_audit JSON object when a summary is present."""
    c, _session = client
    audit = SimpleNamespace(
        event_type="auto_paper_arming_action",
        recorded_at=datetime(2026, 5, 1, 13, 0, 0, tzinfo=timezone.utc),
        action="arm",
        result_status="armed",
        requested_by="ops@example.com",
        reason="Approved",
        client_request_id="arm-req-001",
        arming_state_before="disarmed",
        arming_state_after="armed",
        failure_reasons=[],
        warning_codes=[],
    )
    posture = _build_readback_posture_stub(last_audit=audit)
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    last_audit_payload = response.json()["last_audit"]
    assert last_audit_payload is not None
    assert set(last_audit_payload.keys()) == {
        "event_type",
        "recorded_at",
        "action",
        "result_status",
        "requested_by",
        "reason",
        "client_request_id",
        "arming_state_before",
        "arming_state_after",
        "failure_reasons",
        "warning_codes",
    }


def test_get_auto_paper_arming_armed_full_response_shape_is_locked(client, monkeypatch):
    """Full JSON snapshot for a valid armed posture to catch any shape drift."""
    c, _session = client
    posture = _build_readback_posture_stub(
        status="armed",
        arming_state="armed",
        stored_state="armed",
        armed_by="ops@example.com",
        arm_reason="Approved by ops",
        client_request_id="arm-req-001",
        last_enablement_status="ready",
    )
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "armed"
    assert payload["arming_state"] == "armed"
    assert payload["scope"] == "auto_paper"
    assert payload["trading_mode"] == "paper"
    assert payload["evaluated_at"] == "2026-05-01T14:00:00Z"
    assert payload["fail_closed_reason"] is None
    assert payload["durable_row_present"] is True
    assert payload["duplicate_rows_detected"] is False
    assert payload["stored_state"] == "armed"
    assert payload["armed_at"] == "2026-05-01T12:00:00Z"
    assert payload["armed_by"] == "ops@example.com"
    assert payload["arm_reason"] == "Approved by ops"
    assert payload["expires_at"] is None
    assert payload["expired"] is False
    assert payload["last_enablement_checked_at"] is None
    assert payload["last_enablement_status"] == "ready"
    assert payload["last_enablement_blockers"] == []
    assert payload["last_enablement_warnings"] == []
    assert payload["client_request_id"] == "arm-req-001"
    assert payload["disarmed_at"] is None
    assert payload["disarmed_by"] is None
    assert payload["disarm_reason"] is None
    assert payload["last_audit"] is None


def test_get_auto_paper_arming_disarmed_full_response_shape_is_locked(client, monkeypatch):
    """Full JSON snapshot for an intentionally disarmed posture."""
    c, _session = client
    posture = _build_readback_posture_stub(
        status="disarmed",
        arming_state="disarmed",
        stored_state="disarmed",
        armed_by=None,
        arm_reason=None,
        fail_closed_reason=None,
        disarmed_by="ops@example.com",
        disarm_reason="Manual reset",
        client_request_id=None,
    )
    posture.armed_at = None
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "disarmed"
    assert payload["arming_state"] == "disarmed"
    assert payload["scope"] == "auto_paper"
    assert payload["trading_mode"] == "paper"
    assert payload["evaluated_at"] == "2026-05-01T14:00:00Z"
    assert payload["fail_closed_reason"] is None
    assert payload["durable_row_present"] is True
    assert payload["duplicate_rows_detected"] is False
    assert payload["stored_state"] == "disarmed"
    assert payload["armed_at"] is None
    assert payload["armed_by"] is None
    assert payload["arm_reason"] is None
    assert payload["expires_at"] is None
    assert payload["expired"] is False
    assert payload["disarmed_by"] == "ops@example.com"
    assert payload["disarm_reason"] == "Manual reset"
    assert payload["client_request_id"] is None
    assert payload["last_audit"] is None


def test_get_auto_paper_arming_fail_closed_full_response_shape_is_locked(client, monkeypatch):
    """Full JSON snapshot for a fail_closed posture to pin exact shape and HTTP 200 semantics."""
    c, _session = client
    posture = _build_readback_posture_stub(
        status="fail_closed",
        arming_state="disarmed",
        fail_closed_reason="durable_state_duplicate",
        stored_state=None,
        durable_row_present=True,
        duplicate_rows_detected=True,
        armed_by=None,
        arm_reason=None,
        client_request_id=None,
    )
    posture.armed_at = None
    _configure_auto_paper_readback_dependencies(monkeypatch, posture=posture)

    response = c.get("/market-data/auto-paper/arming")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail_closed"
    assert payload["arming_state"] == "disarmed"
    assert payload["fail_closed_reason"] == "durable_state_duplicate"
    assert payload["durable_row_present"] is True
    assert payload["duplicate_rows_detected"] is True
    assert payload["stored_state"] is None
    assert payload["armed_at"] is None
    assert payload["armed_by"] is None
    assert payload["arm_reason"] is None
    assert payload["disarmed_by"] is None
    assert payload["disarm_reason"] is None
    assert payload["client_request_id"] is None
    assert payload["last_audit"] is None


# ---------------------------------------------------------------------------
# POST /market-data/auto-paper/arming/disarm  (MH-138 disarm endpoint)
# ---------------------------------------------------------------------------


def _configure_auto_paper_disarm_dependencies(
    monkeypatch,
    *,
    posture,
    disarm_error=None,
    execution_control="manual",
):
    """Minimal stub for POST /auto-paper/arming/disarm.

    Wires TradingControlArmingStateService and get_trading_mode; does not
    touch broker, scheduler, or enablement surfaces.
    """
    disarm_calls: list[dict] = []

    class StubDisarmService:
        def __init__(self, session):
            _ = session

        def get_readback_posture(self, *, scope="auto_paper", trading_mode="paper", now=None):
            _ = (scope, trading_mode, now)
            return posture

        def disarm_state(self, **kwargs):
            disarm_calls.append(kwargs)
            if disarm_error is not None:
                raise disarm_error

    monkeypatch.setattr(market_data_route, "TradingControlArmingStateService", StubDisarmService)
    monkeypatch.setattr(
        market_data_route,
        "get_trading_mode",
        lambda: SimpleNamespace(
            trading_mode="paper",
            execution_control=execution_control,
            arming_state="armed",
            live_order_submission_allowed=False,
            paper_order_submission_allowed=True,
            auto_trading_allowed=False,
            emergency_stop_active=False,
            reasons=(),
        ),
    )

    return disarm_calls


def _armed_posture():
    return _build_readback_posture_stub(
        status="armed",
        arming_state="armed",
        stored_state="armed",
    )


def _disarmed_posture():
    return _build_readback_posture_stub(
        status="disarmed",
        arming_state="disarmed",
        stored_state="disarmed",
        armed_by=None,
        arm_reason=None,
    )


def _fail_closed_posture(reason):
    return _build_readback_posture_stub(
        status="fail_closed",
        arming_state="disarmed",
        stored_state=None,
        fail_closed_reason=reason,
        durable_row_present=reason != "durable_state_missing",
    )


def _disarm_body(**kwargs):
    body = {"requested_by": "ops@example.com", "reason": "Operator disarm", "client_request_id": "dis-req-001"}
    body.update(kwargs)
    return body


def test_post_auto_paper_disarm_disarms_when_currently_armed(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    disarm_calls = _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_armed_posture())
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "disarmed"
    assert payload["arming_state"] == "disarmed"
    assert payload["failure_reasons"] == []
    assert payload["audit_recorded"] is True
    assert payload["audit_event_type"] == "auto_paper_arming_action"
    assert payload["requested_by"] == "ops@example.com"
    assert payload["reason"] == "Operator disarm"
    assert payload["client_request_id"] == "dis-req-001"
    assert len(disarm_calls) == 1
    assert disarm_calls[0]["disarmed_by"] == "ops@example.com"
    assert disarm_calls[0]["disarm_reason"] == "Operator disarm"


def test_post_auto_paper_disarm_disarms_when_expired_armed(client, monkeypatch):
    """Expired armed state is allowed to disarm as an explicit cleanup path."""
    c, _session = client
    arming_events: list[dict] = []
    expired_posture = _build_readback_posture_stub(
        status="fail_closed",
        arming_state="disarmed",
        fail_closed_reason="durable_state_expired",
        stored_state="armed",
        expired=True,
    )
    disarm_calls = _configure_auto_paper_disarm_dependencies(monkeypatch, posture=expired_posture)
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "disarmed"
    assert payload["failure_reasons"] == []
    assert len(disarm_calls) == 1


def test_post_auto_paper_disarm_rejects_when_already_disarmed(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    disarm_calls = _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_disarmed_posture())
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert payload["arming_state"] == "disarmed"
    assert "already_disarmed" in payload["failure_reasons"]
    assert len(disarm_calls) == 0


@pytest.mark.parametrize("fail_reason,expected_code", [
    ("durable_state_missing", "durable_state_missing"),
    ("durable_state_duplicate", "durable_state_duplicate"),
    ("durable_state_invalid", "durable_state_invalid"),
    ("durable_state_read_failed", "durable_arming_state_read_failed"),
])
def test_post_auto_paper_disarm_rejects_fail_closed_durable_states(
    client, monkeypatch, fail_reason, expected_code
):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_fail_closed_posture(fail_reason))
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert expected_code in payload["failure_reasons"]


def test_post_auto_paper_disarm_fails_closed_when_durable_write_fails(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(
        monkeypatch,
        posture=_armed_posture(),
        disarm_error=RuntimeError("db write failed"),
    )
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "durable_arming_state_write_failed" in payload["failure_reasons"]
    assert payload["audit_recorded"] is True


def test_post_auto_paper_disarm_rejects_missing_requested_by(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_armed_posture())
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body(requested_by=""))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "requested_by_required" in payload["failure_reasons"]


def test_post_auto_paper_disarm_rejects_missing_reason(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_armed_posture())
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body(reason=""))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "operator_reason_required" in payload["failure_reasons"]


def test_post_auto_paper_disarm_records_audit_on_success(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_armed_posture())
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert len(arming_events) == 1
    ev = arming_events[0]
    assert ev["action"] == "disarm"
    assert ev["result_status"] == "disarmed"
    assert ev["requested_by"] == "ops@example.com"
    assert ev["reason"] == "Operator disarm"
    assert ev["failure_reasons"] == []
    assert ev["arming_state_before"] == "armed"
    assert ev["arming_state_after"] == "disarmed"
    assert ev["trading_mode"] == "paper"
    assert ev["execution_control"] == "manual"


def test_post_auto_paper_disarm_records_audit_on_rejection(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_disarmed_posture())
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw)),
    })())

    c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert len(arming_events) == 1
    ev = arming_events[0]
    assert ev["action"] == "disarm"
    assert ev["result_status"] == "rejected"
    assert "already_disarmed" in ev["failure_reasons"]


def test_post_auto_paper_disarm_response_field_set_is_locked(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_armed_posture())
    monkeypatch.setattr(market_data_route, "audit_log_service", type("AL", (), {
        "log_auto_paper_arming_action": staticmethod(lambda **kw: None),
    })())

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }


def test_post_auto_paper_disarm_failure_code_vocab_is_locked():
    assert market_data_route._AUTO_PAPER_DISARM_FAILURE_CODE_DESCRIPTIONS == {
        "already_disarmed": "The auto-paper arming surface is already in the disarmed state.",
        "durable_state_missing": "No durable arming-state row found; cannot safely disarm.",
        "durable_state_duplicate": "Duplicate durable arming-state rows detected; cannot safely disarm.",
        "durable_state_invalid": "The durable arming-state row is in an invalid state; cannot safely disarm.",
        "durable_arming_state_read_failed": "A DB exception prevented reading the current arming state.",
        "durable_arming_state_write_failed": "The durable disarm-state write failed; the disarm mutation was rejected fail-closed.",
        "operator_reason_required": "A non-empty disarm reason is required.",
        "requested_by_required": "A non-empty requested_by value is required.",
    }


# ---------------------------------------------------------------------------
# MH-139 — Auto Paper Arming Disarm Endpoint Contract Review
# Contract-lock tests: request/response model field sets, full per-posture
# response snapshots, and audit key boundary checks.
# ---------------------------------------------------------------------------


def test_auto_paper_disarm_request_pydantic_field_set_is_locked():
    assert set(market_data_route.AutoPaperDisarmRequest.model_fields.keys()) == {
        "requested_by",
        "reason",
        "client_request_id",
    }


def test_auto_paper_disarm_response_pydantic_field_set_is_locked():
    assert set(market_data_route.AutoPaperDisarmResponse.model_fields.keys()) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }


def test_post_auto_paper_disarm_success_full_response_shape_is_locked(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_armed_posture())
    monkeypatch.setattr(
        market_data_route,
        "audit_log_service",
        type("AL", (), {"log_auto_paper_arming_action": staticmethod(lambda **kw: None)})(),
    )

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }
    assert payload["status"] == "disarmed"
    assert payload["arming_state"] == "disarmed"
    assert payload["failure_reasons"] == []
    assert payload["audit_recorded"] is True
    assert payload["audit_event_type"] == "auto_paper_arming_action"
    assert payload["requested_by"] == "ops@example.com"
    assert payload["reason"] == "Operator disarm"
    assert payload["client_request_id"] == "dis-req-001"
    assert datetime.fromisoformat(payload["evaluated_at"].replace("Z", "+00:00"))


def test_post_auto_paper_disarm_already_disarmed_full_response_shape_is_locked(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_disarmed_posture())
    monkeypatch.setattr(
        market_data_route,
        "audit_log_service",
        type("AL", (), {"log_auto_paper_arming_action": staticmethod(lambda **kw: None)})(),
    )

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }
    assert payload["status"] == "rejected"
    assert payload["arming_state"] == "disarmed"
    assert payload["failure_reasons"] == ["already_disarmed"]
    assert payload["audit_recorded"] is True
    assert payload["audit_event_type"] == "auto_paper_arming_action"
    assert payload["requested_by"] == "ops@example.com"
    assert payload["reason"] == "Operator disarm"
    assert payload["client_request_id"] == "dis-req-001"
    assert datetime.fromisoformat(payload["evaluated_at"].replace("Z", "+00:00"))


def test_post_auto_paper_disarm_fail_closed_full_response_shape_is_locked(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_fail_closed_posture("durable_state_duplicate"))
    monkeypatch.setattr(
        market_data_route,
        "audit_log_service",
        type("AL", (), {"log_auto_paper_arming_action": staticmethod(lambda **kw: None)})(),
    )

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }
    assert payload["status"] == "rejected"
    assert payload["arming_state"] == "disarmed"
    assert payload["failure_reasons"] == ["durable_state_duplicate"]
    assert payload["audit_recorded"] is True
    assert payload["audit_event_type"] == "auto_paper_arming_action"
    assert payload["requested_by"] == "ops@example.com"
    assert payload["reason"] == "Operator disarm"
    assert payload["client_request_id"] == "dis-req-001"
    assert datetime.fromisoformat(payload["evaluated_at"].replace("Z", "+00:00"))


def test_post_auto_paper_disarm_durable_write_failure_full_response_shape_is_locked(client, monkeypatch):
    c, _session = client
    _configure_auto_paper_disarm_dependencies(
        monkeypatch,
        posture=_armed_posture(),
        disarm_error=RuntimeError("simulated write failure"),
    )
    monkeypatch.setattr(
        market_data_route,
        "audit_log_service",
        type("AL", (), {"log_auto_paper_arming_action": staticmethod(lambda **kw: None)})(),
    )

    response = c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "status",
        "arming_state",
        "evaluated_at",
        "failure_reasons",
        "audit_recorded",
        "audit_event_type",
        "requested_by",
        "reason",
        "client_request_id",
    }
    assert payload["status"] == "rejected"
    assert payload["arming_state"] == "armed"
    assert payload["failure_reasons"] == ["durable_arming_state_write_failed"]
    assert payload["audit_recorded"] is True
    assert payload["audit_event_type"] == "auto_paper_arming_action"
    assert payload["requested_by"] == "ops@example.com"
    assert payload["reason"] == "Operator disarm"
    assert payload["client_request_id"] == "dis-req-001"
    assert datetime.fromisoformat(payload["evaluated_at"].replace("Z", "+00:00"))


def test_post_auto_paper_disarm_audit_success_key_boundary_is_locked(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_armed_posture())
    monkeypatch.setattr(
        market_data_route,
        "audit_log_service",
        type("AL", (), {"log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw))})(),
    )

    c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert len(arming_events) == 1
    event = arming_events[0]
    assert set(event.keys()) == {
        "action",
        "requested_by",
        "reason",
        "result_status",
        "client_request_id",
        "failure_reasons",
        "trading_mode",
        "execution_control",
        "arming_state_before",
        "arming_state_after",
    }
    assert event["action"] == "disarm"
    assert event["result_status"] == "disarmed"
    assert event["failure_reasons"] == []
    assert event["arming_state_before"] == "armed"
    assert event["arming_state_after"] == "disarmed"


def test_post_auto_paper_disarm_audit_rejection_key_boundary_is_locked(client, monkeypatch):
    c, _session = client
    arming_events: list[dict] = []
    _configure_auto_paper_disarm_dependencies(monkeypatch, posture=_disarmed_posture())
    monkeypatch.setattr(
        market_data_route,
        "audit_log_service",
        type("AL", (), {"log_auto_paper_arming_action": staticmethod(lambda **kw: arming_events.append(kw))})(),
    )

    c.post("/market-data/auto-paper/arming/disarm", json=_disarm_body())

    assert len(arming_events) == 1
    event = arming_events[0]
    assert set(event.keys()) == {
        "action",
        "requested_by",
        "reason",
        "result_status",
        "client_request_id",
        "failure_reasons",
        "trading_mode",
        "execution_control",
        "arming_state_before",
        "arming_state_after",
    }
    assert event["action"] == "disarm"
    assert event["result_status"] == "rejected"
    assert event["failure_reasons"] == ["already_disarmed"]
    assert event["arming_state_before"] == "disarmed"
    assert event["arming_state_after"] == "disarmed"
