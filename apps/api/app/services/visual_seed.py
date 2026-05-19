"""Shared visual seed tagging and filtering helpers.

Visual seed data is intentionally created for UI previews only. It must be
excluded from production reporting, learning, and live metrics unless an
explicit preview mode is requested.
"""

from __future__ import annotations

from sqlalchemy import or_


VISUAL_SEED_PROVIDER = "visual_seed_demo"

VISUAL_SEED_TAGS: dict[str, object] = {
    "data_origin": "visual_seed",
    "environment": "demo",
    "exclude_from_reporting": True,
    "exclude_from_learning": True,
    "exclude_from_live_metrics": True,
}


def with_visual_seed_tags(payload: dict[str, object] | None = None) -> dict[str, object]:
    """Return payload extended with canonical visual seed metadata tags."""
    data = dict(payload or {})
    data.update(VISUAL_SEED_TAGS)
    return data


def provider_filter(column, *, include_visual_seed: bool):
    """Return SQLAlchemy filter condition for optional visual seed inclusion."""
    if include_visual_seed:
        return True
    return or_(column.is_(None), column != VISUAL_SEED_PROVIDER)
