"""MH-DRIFTLOCK-PAPER-VALIDATION-EVENT-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.paper_validation_event import PaperValidationEvent

_EXPECTED: frozenset[str] = frozenset(
    {"created_at", "event_type", "id", "message", "paper_validation_plan_id", "payload"}
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "paper_validation_plan_id", "event_type", "created_at"}
)


def test_paper_validation_event_full_column_catalog() -> None:
    actual = frozenset(c.name for c in PaperValidationEvent.__table__.columns)
    assert actual == _EXPECTED, f"PaperValidationEvent column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_paper_validation_event_safety_subset_present() -> None:
    actual = frozenset(c.name for c in PaperValidationEvent.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
