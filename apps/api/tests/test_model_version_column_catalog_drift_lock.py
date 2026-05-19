"""MH-DRIFTLOCK-MODEL-VERSION-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.model_version import ModelVersion

_EXPECTED: frozenset[str] = frozenset(
    {"alias_name", "created_at", "id", "is_active", "max_output_tokens",
     "model_name", "notes", "provider", "provider_name", "reasoning_level",
     "supports_structured_output", "temperature", "top_p"}
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "model_name", "provider", "is_active"}
)


def test_model_version_full_column_catalog() -> None:
    actual = frozenset(c.name for c in ModelVersion.__table__.columns)
    assert actual == _EXPECTED, f"ModelVersion column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_model_version_safety_subset_present() -> None:
    actual = frozenset(c.name for c in ModelVersion.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
