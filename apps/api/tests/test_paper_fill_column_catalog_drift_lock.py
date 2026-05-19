"""MH-DRIFTLOCK-PAPER-FILL-COLUMN-CATALOG"""
from __future__ import annotations

from app.db.models.paper_fill import PaperFill

_EXPECTED: frozenset[str] = frozenset(
    {"created_at", "fee_amount", "fill_price", "fill_qty", "fill_ts", "id", "paper_order_id", "slippage_bps"}
)
_SAFETY: frozenset[str] = frozenset(
    {"id", "paper_order_id", "fill_price", "fill_qty", "fill_ts"}
)


def test_paper_fill_full_column_catalog() -> None:
    actual = frozenset(c.name for c in PaperFill.__table__.columns)
    assert actual == _EXPECTED, f"PaperFill column drift: missing={_EXPECTED - actual} extra={actual - _EXPECTED}"


def test_paper_fill_safety_subset_present() -> None:
    actual = frozenset(c.name for c in PaperFill.__table__.columns)
    missing = _SAFETY - actual
    assert not missing, f"PaperFill safety subset missing: {sorted(missing)}"
    assert _SAFETY.issubset(_EXPECTED)
