"""refresh_universe_job — refresh the instrument/symbol master list.

Usage:
    python -m apps.learning.jobs.refresh_universe_job
"""

from __future__ import annotations

import asyncio


async def main() -> None:
    # Stub: full implementation queries broker/provider for active symbols
    print("[stub] Universe refresh job — not yet implemented")


if __name__ == "__main__":
    asyncio.run(main())
