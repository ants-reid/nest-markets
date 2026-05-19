"""MH-DRIFTLOCK-PAPER-VALIDATION-EVIDENCE-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.paper_validation_evidence import PaperValidationEvidence

_EXPECTED: frozenset[str] = frozenset(
    {
        "asset", "closed_at", "confidence", "created_at", "entry_price", "exit_price",
        "id", "included_in_metrics", "notes", "opened_at", "paper_validation_plan_id",
        "payload", "pnl_amount", "pnl_pct", "r_multiple", "result", "side",
        "source_id", "source_type", "timeframe", "updated_at",
    }
)
_SAFETY: frozenset[str] = frozenset(
    {
        "id", "paper_validation_plan_id", "asset", "side", "result",
        "opened_at", "closed_at", "pnl_amount", "included_in_metrics",
    }
)


def test_paper_validation_evidence_full_column_catalog() -> None:
    actual = frozenset(c.name for c in PaperValidationEvidence.__table__.columns)
    assert actual == _EXPECTED, f"PaperValidationEvidence column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_paper_validation_evidence_safety_subset_present() -> None:
    actual = frozenset(c.name for c in PaperValidationEvidence.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
