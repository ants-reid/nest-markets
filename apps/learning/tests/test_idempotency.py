"""Phase 6 — idempotency tests for backfill services.

These tests verify that running a backfill job twice does not raise errors
and produces stable results (idempotent behaviour).
"""

from __future__ import annotations

import asyncio
from datetime import date

from apps.learning.services.backfill.bars_backfill_service import BarsBackfillService
from apps.learning.services.backfill.news_backfill_service import NewsBackfillService
from apps.learning.services.backfill.macro_backfill_service import MacroBackfillService


def test_bars_backfill_idempotent():
    svc = BarsBackfillService()
    start = date(2024, 1, 1)
    end = date(2024, 1, 5)
    r1 = asyncio.run(svc.run("SPY", "1D", start, end))
    r2 = asyncio.run(svc.run("SPY", "1D", start, end))
    assert r1 == r2


def test_news_backfill_idempotent():
    svc = NewsBackfillService()
    r1 = asyncio.run(svc.run(["AAPL"]))
    r2 = asyncio.run(svc.run(["AAPL"]))
    assert r1 == r2


def test_macro_backfill_idempotent():
    svc = MacroBackfillService()
    r1 = asyncio.run(svc.run("FEDFUNDS", start=date(2020, 1, 1), end=date(2020, 12, 31)))
    r2 = asyncio.run(svc.run("FEDFUNDS", start=date(2020, 1, 1), end=date(2020, 12, 31)))
    assert r1 == r2
