"""Tests for MH-FEED-MONITOR-001 feed monitor service."""

from __future__ import annotations

import asyncio

from app.schemas.feed_monitor import FeedMonitorRowSchema
from app.services.feed_monitor_service import get_feed_monitor_snapshot
from app.services.provider_inventory_service import ProviderInventoryRow


def test_feed_monitor_snapshot_rolls_up_provider_and_runtime_rows(monkeypatch):
    def _fake_inventory() -> list[ProviderInventoryRow]:
        return [
            ProviderInventoryRow(
                name="feeds_in.polygon_provider",
                category="feeds_in",
                status="degraded",
                configured=False,
                detail="POLYGON_API_KEY missing",
                latency_ms=1.2,
                checked_at="2026-05-19T10:00:00Z",
                extra={},
            ),
            ProviderInventoryRow(
                name="feeds_out.openai_provider",
                category="feeds_out",
                status="ok",
                configured=True,
                detail="OPENAI_API_KEY configured",
                latency_ms=1.1,
                checked_at="2026-05-19T10:00:01Z",
                extra={},
            ),
        ]

    async def _fake_runtime() -> FeedMonitorRowSchema:
        return FeedMonitorRowSchema(
            id="runtime.ibkr_gateway",
            name="runtime.ibkr_gateway",
            category="runtime",
            kind="broker_gateway_runtime",
            status="ok",
            configured=True,
            runtime_reachable=True,
            detail="gateway reachable",
            action="No immediate action required.",
            checked_at="2026-05-19T10:00:02Z",
            latency_ms=3.4,
            target="http://ibkr-gateway",
            tags=["paper", "broker", "runtime"],
            extra={},
        )

    monkeypatch.setattr(
        "app.services.feed_monitor_service.list_provider_inventory",
        _fake_inventory,
    )
    monkeypatch.setattr(
        "app.services.feed_monitor_service._build_broker_runtime_row",
        _fake_runtime,
    )

    snapshot = asyncio.run(get_feed_monitor_snapshot())

    assert snapshot.overall == "degraded"
    assert snapshot.summary.total == 3
    assert snapshot.summary.configured == 2
    assert snapshot.summary.runtime_reachable == 1
    assert snapshot.summary.by_category == {"feeds_in": 1, "feeds_out": 1, "runtime": 1}
    assert snapshot.summary.by_status == {"degraded": 1, "ok": 2}
    assert snapshot.next_actions == [
        "Configure POLYGON_API_KEY to restore upstream market-data coverage."
    ]
    assert [row.name for row in snapshot.rows] == [
        "feeds_in.polygon_provider",
        "feeds_out.openai_provider",
        "runtime.ibkr_gateway",
    ]
