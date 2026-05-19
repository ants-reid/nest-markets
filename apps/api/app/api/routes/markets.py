"""MH-COCKPIT-01-A — Read-only markets snapshot endpoint.

Wraps ``market_session_service.get_market_snapshot``. Stateless; never
consulted by the broker or trading_control gates.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from app.services.market_session_service import get_market_snapshot

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/snapshot")
def markets_snapshot() -> Dict[str, Any]:
    """Return the current market open/closed snapshot.

    Operator hint only. Does not influence trading decisions.
    """

    return get_market_snapshot()
