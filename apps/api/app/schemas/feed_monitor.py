"""Schemas for the read-only feed monitor surface."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FeedMonitorStatus = Literal["ok", "degraded", "down", "unknown", "error"]
FeedMonitorCategory = Literal["feeds_in", "feeds_out", "runtime"]


class FeedMonitorRowSchema(BaseModel):
    id: str
    name: str
    category: FeedMonitorCategory
    kind: str
    status: FeedMonitorStatus
    configured: bool | None = None
    runtime_reachable: bool | None = None
    detail: str | None = None
    action: str | None = None
    checked_at: str | None = None
    latency_ms: float | None = None
    target: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class FeedMonitorSummarySchema(BaseModel):
    total: int
    configured: int
    runtime_reachable: int
    issue_count: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)


class FeedMonitorResponseSchema(BaseModel):
    overall: FeedMonitorStatus
    advisory: str
    as_of_utc: str
    summary: FeedMonitorSummarySchema
    next_actions: list[str] = Field(default_factory=list)
    rows: list[FeedMonitorRowSchema] = Field(default_factory=list)
