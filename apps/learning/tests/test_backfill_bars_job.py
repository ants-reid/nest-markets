"""Phase 6 — bars backfill job tests."""

from __future__ import annotations

import asyncio
from datetime import date

from apps.learning.services.backfill.bars_backfill_service import BarsBackfillService


def test_bars_backfill_run_returns_int():
    svc = BarsBackfillService()
    result = asyncio.run(svc.run("AAPL", "1D", date(2024, 1, 1), date(2024, 1, 31)))
    assert isinstance(result, int)


def test_bars_backfill_list_gaps_returns_ranges():
    svc = BarsBackfillService()
    gaps = asyncio.run(
        svc.list_gaps("AAPL", "1D", date(2024, 1, 1), date(2024, 1, 31))
    )
    assert isinstance(gaps, list)
    for start, end in gaps:
        assert start <= end
