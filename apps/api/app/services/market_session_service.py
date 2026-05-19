"""MH-COCKPIT-01-A — Pure-function market-session calendar.

Stateless, dependency-free service that reports whether a small set of
markets is currently open. Calendar is hardcoded; this is intentional —
the Cockpit "markets-open snapshot" is a coarse operator hint, not a
trading-decision input. It is never consulted by the broker, by
``trading_control_service``, or by the order path.

Drift-lock guarantee:
* Pure functions — no DB, no I/O, no external calls.
* Never invoked by any auto/live enforcement path.
* Approximate calendar; ignores holidays by design (clearly documented).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MarketDefinition:
    code: str
    label: str
    timezone: str
    # 5-tuple: (open_h, open_m, close_h, close_m, weekdays_mask)
    # weekdays_mask: tuple of Monday=0..Sunday=6 ints when the market is open.
    open_time: Tuple[int, int]
    close_time: Tuple[int, int]
    open_weekdays: Tuple[int, ...]
    notes: str


# Hardcoded coarse session calendar. Operator hint only — does NOT feed the
# trading path. Holidays are intentionally not modelled here; surface that to
# the operator via the ``notes`` field so they don't rely on this for
# go/no-go decisions.
_MARKETS: Tuple[MarketDefinition, ...] = (
    MarketDefinition(
        code="FX",
        label="FX (24x5)",
        timezone="UTC",
        open_time=(22, 0),  # Sunday 22:00 UTC
        close_time=(22, 0),  # Friday 22:00 UTC
        open_weekdays=(0, 1, 2, 3, 4, 6),  # Mon–Fri + Sun (open evening)
        notes="Approximate 24x5; rolls open Sunday 22:00 UTC, closes Friday 22:00 UTC.",
    ),
    MarketDefinition(
        code="NYSE",
        label="NYSE / NASDAQ regular session",
        timezone="America/New_York",
        open_time=(9, 30),
        close_time=(16, 0),
        open_weekdays=(0, 1, 2, 3, 4),
        notes="Regular session only; pre/post-market and US holidays not modelled.",
    ),
    MarketDefinition(
        code="LSE",
        label="London Stock Exchange",
        timezone="Europe/London",
        open_time=(8, 0),
        close_time=(16, 30),
        open_weekdays=(0, 1, 2, 3, 4),
        notes="Regular session only; UK bank holidays not modelled.",
    ),
    MarketDefinition(
        code="TSE",
        label="Tokyo Stock Exchange",
        timezone="Asia/Tokyo",
        # Combined morning + afternoon session window for simplicity. The
        # midday lunch break is intentionally not modelled because this is
        # an operator hint surface, not a trading-decision input.
        open_time=(9, 0),
        close_time=(15, 0),
        open_weekdays=(0, 1, 2, 3, 4),
        notes="Combined window; 11:30–12:30 lunch break and JP holidays not modelled.",
    ),
)


def _is_open(definition: MarketDefinition, now_utc: datetime) -> bool:
    """Return True if ``definition`` is open at ``now_utc``."""

    if definition.code == "FX":
        # Special-case the rolling weekly window:
        # Open from Sunday 22:00 UTC through Friday 22:00 UTC.
        weekday = now_utc.weekday()  # Monday=0..Sunday=6
        if weekday == 5:  # Saturday
            return False
        if weekday == 6:  # Sunday
            return now_utc.hour >= 22
        if weekday == 4:  # Friday
            return now_utc.hour < 22
        return True

    local = now_utc.astimezone(ZoneInfo(definition.timezone))
    if local.weekday() not in definition.open_weekdays:
        return False
    open_t = time(*definition.open_time)
    close_t = time(*definition.close_time)
    local_t = local.time()
    return open_t <= local_t < close_t


def get_market_snapshot(now_utc: Optional[datetime] = None) -> dict:
    """Return a snapshot of market open/closed states.

    Pure function. ``now_utc`` is injectable for testing.
    """

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    markets: List[dict] = []
    for definition in _MARKETS:
        local = now_utc.astimezone(ZoneInfo(definition.timezone)) if definition.timezone != "UTC" else now_utc
        markets.append(
            {
                "code": definition.code,
                "label": definition.label,
                "timezone": definition.timezone,
                "is_open": _is_open(definition, now_utc),
                "local_time": local.isoformat(),
                "open_time": f"{definition.open_time[0]:02d}:{definition.open_time[1]:02d}",
                "close_time": f"{definition.close_time[0]:02d}:{definition.close_time[1]:02d}",
                "open_weekdays": list(definition.open_weekdays),
                "notes": definition.notes,
            }
        )

    return {
        "as_of_utc": now_utc.isoformat(),
        "markets": markets,
        "advisory": (
            "Operator hint only. Does not feed the trading path. Holidays and "
            "early-close days are not modelled."
        ),
    }
