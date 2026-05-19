"""backfill_filings_job — historical SEC filing events ingestion job.

Usage:
    python -m apps.learning.jobs.backfill_filings_job \\
        --symbols AAPL MSFT --form-types 10-K 10-Q
"""

from __future__ import annotations

import argparse
import asyncio


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill historical SEC filings")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--form-types", nargs="+", default=["10-K", "10-Q", "8-K"])
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    # Stub: full implementation wires SECAdapter and FilingEvent model
    print(f"[stub] Would backfill {args.form_types} filings for {args.symbols}")


if __name__ == "__main__":
    asyncio.run(main())
