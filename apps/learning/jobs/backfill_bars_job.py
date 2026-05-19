"""backfill_bars_job — historical OHLCV bar ingestion job.

Usage:
    python -m apps.learning.jobs.backfill_bars_job \\
        --symbol AAPL --timeframe 1D \\
        --start 2020-01-01 --end 2024-12-31

The job delegates to BarsBackfillService and is idempotent: bars that
already exist in the DB are skipped.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date

from apps.learning.services.backfill.bars_backfill_service import BarsBackfillService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill historical OHLCV bars")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1D")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", default=str(date.today()), type=date.fromisoformat)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    svc = BarsBackfillService()
    count = await svc.run(args.symbol, args.timeframe, args.start, args.end)
    print(f"Backfilled {count} bars for {args.symbol} ({args.timeframe})")


if __name__ == "__main__":
    asyncio.run(main())
