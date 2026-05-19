"""MH-FEED-MONITOR-001 — Read-only ``/monitor/feeds`` endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.feed_monitor import FeedMonitorResponseSchema
from app.services.feed_monitor_service import get_feed_monitor_snapshot

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/feeds", response_model=FeedMonitorResponseSchema)
async def read_feed_monitor() -> FeedMonitorResponseSchema:
    """Return consolidated API and data-feed posture.

    Read-only aggregator over existing probe/configuration surfaces plus a
    lightweight broker runtime reachability check. Never mutates providers,
    broker controls, or trading safety state.
    """
    return await get_feed_monitor_snapshot()
