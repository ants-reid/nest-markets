"""MH-DRIFTLOCK-PROMPT-VERSION-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.prompt_version import PromptVersion

_EXPECTED: frozenset[str] = frozenset(
    {"created_at", "id", "is_active", "name", "notes", "role",
     "schema_json", "system_prompt", "user_template", "version"}
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "name", "version", "role", "is_active"}
)


def test_prompt_version_full_column_catalog() -> None:
    actual = frozenset(c.name for c in PromptVersion.__table__.columns)
    assert actual == _EXPECTED, f"PromptVersion column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_prompt_version_safety_subset_present() -> None:
    actual = frozenset(c.name for c in PromptVersion.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
