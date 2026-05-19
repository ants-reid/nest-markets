"""backfill_news_job — historical news ingestion job.

Usage:
    python -m apps.learning.jobs.backfill_news_job \\
        --symbols AAPL MSFT --limit 200
"""

from __future__ import annotations

import argparse
import asyncio

from apps.learning.services.backfill.news_backfill_service import NewsBackfillService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill historical news articles")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    svc = NewsBackfillService()
    count = await svc.run(args.symbols, limit=args.limit)
    print(f"Ingested {count} news records for {args.symbols}")


if __name__ == "__main__":
    asyncio.run(main())
