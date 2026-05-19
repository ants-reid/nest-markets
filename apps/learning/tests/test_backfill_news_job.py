"""Phase 6 — news backfill job tests."""

from __future__ import annotations

import asyncio

from apps.learning.services.backfill.news_backfill_service import NewsBackfillService


def test_news_backfill_run_returns_int():
    svc = NewsBackfillService()
    result = asyncio.run(svc.run(["AAPL", "TSLA"], limit=10))
    assert isinstance(result, int)
