"""backfill_macro_job — historical macroeconomic series ingestion job.

Usage:
    python -m apps.learning.jobs.backfill_macro_job \\
        --series FEDFUNDS CPIAUCSL --start 2015-01-01
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date

from apps.learning.services.backfill.macro_backfill_service import MacroBackfillService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill macro time series")
    parser.add_argument("--series", nargs="+", required=True)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", default=str(date.today()), type=date.fromisoformat)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    svc = MacroBackfillService()
    total = 0
    for code in args.series:
        count = await svc.run(code, start=args.start, end=args.end)
        print(f"  {code}: {count} observations")
        total += count
    print(f"Total: {total} macro observations")


if __name__ == "__main__":
    asyncio.run(main())
