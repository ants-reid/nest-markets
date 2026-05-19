"""MH-DRIFTLOCK-PAPER-RECOMMENDATION-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.paper_recommendation import PaperRecommendation

_EXPECTED: frozenset[str] = frozenset(
    {
        "confidence", "created_at", "estimated_notional", "executed_at", "id",
        "limit_price", "model_version_id", "order_type", "paper_order_ids", "quantity",
        "rationale", "review_notes", "reviewed_at", "reviewed_by", "risk_score",
        "side", "signal_id", "source_metadata", "status", "ticker",
    }
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "signal_id", "ticker", "side", "quantity", "status", "executed_at", "reviewed_by"}
)


def test_paper_recommendation_full_column_catalog() -> None:
    actual = frozenset(c.name for c in PaperRecommendation.__table__.columns)
    assert actual == _EXPECTED, f"PaperRecommendation column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_paper_recommendation_safety_subset_present() -> None:
    actual = frozenset(c.name for c in PaperRecommendation.__table__.columns)
    missing = _SAFETY - actual
    assert not missing
    assert _SAFETY.issubset(_EXPECTED)
