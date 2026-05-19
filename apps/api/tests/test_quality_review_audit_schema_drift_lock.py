"""Cycle 43 — Schema drift-lock for ``quality_review_audits`` (MH-13).

Locks the append-only audit trail of operator triage decisions on
data-quality reports.

Pinned shape:
  * 9 business columns + nullability + String lengths
    (asset_symbol=50, timeframe=10, provider=100, previous_status=50,
    new_status=50, reviewed_by=255)
  * NOT-NULL FK ``report_id → market_data_quality_reports.id`` with
    ``ondelete="CASCADE"`` (audit rows must always link back to a
    real report)
  * ``report_id`` indexed (dominant query axis)
  * Required identity fields (report_id, asset_symbol, timeframe,
    new_status, reviewed_at) carry no silent defaults — a default
    'reviewed' status, for example, would let a report be silently
    auto-cleared by an empty insert.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String, Text

from app.db.models.quality_review_audit import QualityReviewAudit


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "report_id": (False, None, None),  # UUID FK
    "asset_symbol": (False, String, 50),
    "timeframe": (False, String, 10),
    "provider": (True, String, 100),
    "previous_status": (True, String, 50),
    "new_status": (False, String, 50),
    "review_notes": (True, Text, None),
    "reviewed_by": (True, String, 255),
    "reviewed_at": (False, DateTime, None),
}


def test_table_name_unchanged():
    assert QualityReviewAudit.__tablename__ == "quality_review_audits"


def test_business_column_set_unchanged():
    table_cols = set(QualityReviewAudit.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"QualityReviewAudit is missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"QualityReviewAudit has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = QualityReviewAudit.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"QualityReviewAudit.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = QualityReviewAudit.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"QualityReviewAudit.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_report_id_fk_unchanged_with_cascade():
    """report_id must remain FK to market_data_quality_reports.id with
    CASCADE delete, NOT NULL, indexed."""
    col = QualityReviewAudit.__table__.columns["report_id"]
    assert col.nullable is False
    assert col.index is True, (
        "QualityReviewAudit.report_id must remain indexed."
    )
    fks = list(col.foreign_keys)
    assert len(fks) == 1, "report_id must keep exactly one FK."
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "market_data_quality_reports.id", (
        f"FK target drifted: got {fk.target_fullname!r}."
    )
    assert (fk.ondelete or "").upper() == "CASCADE", (
        f"FK ondelete must remain CASCADE; got {fk.ondelete!r}."
    )


def test_required_identity_fields_have_no_silent_defaults():
    """A default 'reviewed' new_status would let an empty insert
    silently auto-clear a report."""
    for col_name in ("report_id", "asset_symbol", "timeframe", "new_status", "reviewed_at"):
        col = QualityReviewAudit.__table__.columns[col_name]
        assert col.default is None, (
            f"QualityReviewAudit.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"QualityReviewAudit.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = QualityReviewAudit.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in QualityReviewAudit.__table__.primary_key.columns]
    assert pk_cols == ["id"]
