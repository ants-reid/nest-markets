"""Tests for MH-FEED-MONITOR-001 ``GET /monitor/feeds`` route."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.feed_monitor import FeedMonitorResponseSchema, FeedMonitorRowSchema, FeedMonitorSummarySchema


def test_monitor_feeds_route_shape(monkeypatch):
    async def _fake_snapshot() -> FeedMonitorResponseSchema:
        return FeedMonitorResponseSchema(
            overall="degraded",
            advisory="read-only",
            as_of_utc="2026-05-19T10:00:00Z",
            summary=FeedMonitorSummarySchema(
                total=2,
                configured=1,
                runtime_reachable=0,
                issue_count=1,
                by_status={"degraded": 1, "ok": 1},
                by_category={"feeds_in": 1, "runtime": 1},
            ),
            next_actions=["Configure POLYGON_API_KEY to restore upstream market-data coverage."],
            rows=[
                FeedMonitorRowSchema(
                    id="feeds_in.polygon_provider",
                    name="feeds_in.polygon_provider",
                    category="feeds_in",
                    kind="provider_probe",
                    status="degraded",
                    configured=False,
                    detail="missing key",
                    action="Configure POLYGON_API_KEY to restore upstream market-data coverage.",
                    checked_at="2026-05-19T10:00:00Z",
                    latency_ms=1.2,
                    tags=["feeds_in", "probe"],
                    extra={},
                ),
                FeedMonitorRowSchema(
                    id="runtime.ibkr_gateway",
                    name="runtime.ibkr_gateway",
                    category="runtime",
                    kind="broker_gateway_runtime",
                    status="ok",
                    configured=True,
                    runtime_reachable=False,
                    detail="reachable",
                    action="No immediate action required.",
                    checked_at="2026-05-19T10:00:01Z",
                    latency_ms=3.5,
                    tags=["runtime"],
                    extra={},
                ),
            ],
        )

    monkeypatch.setattr(
        "app.api.routes.monitor_feeds.get_feed_monitor_snapshot",
        _fake_snapshot,
    )

    client = TestClient(app)
    resp = client.get("/monitor/feeds")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in ("overall", "advisory", "as_of_utc", "summary", "next_actions", "rows"):
        assert key in body
    assert body["summary"]["total"] == 2
    assert len(body["rows"]) == 2
