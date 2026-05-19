"""Event proximity features — distance to scheduled market events."""

from __future__ import annotations

from datetime import date


def days_to_event(today: date, event_date: date) -> int:
    """Return the number of calendar days until *event_date*.

    Negative values mean the event is in the past.
    """
    return (event_date - today).days


def event_proximity_bucket(days: int) -> str:
    """Classify proximity: 'imminent', 'near', 'medium', 'far', or 'past'."""
    if days < 0:
        return "past"
    if days <= 1:
        return "imminent"
    if days <= 7:
        return "near"
    if days <= 30:
        return "medium"
    return "far"
