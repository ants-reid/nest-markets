"""Cycle 43 — Schema drift-lock for ``research_jobs``.

Locks the persisted lifecycle table for Data Centre import / quality
jobs (dependency surface of MH-02 Historical Import Manager).

Pinned shape:
  * 13 business columns + nullability + String lengths
    (job_type=50, status=50, requested_by=255)
  * job_type and status indexed (dominant query axes)
  * request_payload JSONB-family + NOT NULL
  * result_payload JSONB-family + nullable
  * **ANTI-ESCALATION**: ``status`` defaults to ``'queued'`` (Python
    layer). A fresh row must NEVER default to ``'completed'`` /
    ``'succeeded'`` — that would let a dispatcher mark a job done
    without actually running it.
  * ``progress_current`` / ``progress_total`` default to 0 (no silent
    "always 100% done" defaults)
  * Required identity fields (job_type, request_payload) carry no
    silent defaults.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, Text

from app.db.models.research_job import ResearchJob


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "job_type": (False, String, 50),
    "status": (False, String, 50),
    "requested_by": (True, String, 255),
    "request_payload": (False, None, None),  # JSONB
    "result_payload": (True, None, None),  # JSONB
    "progress_current": (False, Integer, None),
    "progress_total": (False, Integer, None),
    "progress_message": (True, Text, None),
    "error_message": (True, Text, None),
    "retry_of_job_id": (True, None, None),  # UUID
    "started_at": (True, DateTime, None),
    "completed_at": (True, DateTime, None),
    "cancelled_at": (True, DateTime, None),
}


JSONB_COLUMNS: list[str] = ["request_payload", "result_payload"]


def test_table_name_unchanged():
    assert ResearchJob.__tablename__ == "research_jobs"


def test_business_column_set_unchanged():
    table_cols = set(ResearchJob.__table__.columns.keys())
    # ResearchJob uses TimestampMixin → has both created_at and updated_at
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ResearchJob is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ResearchJob has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ResearchJob.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ResearchJob.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ResearchJob.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"ResearchJob.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_jsonb_columns_remain_jsonb_family():
    for col_name in JSONB_COLUMNS:
        col = ResearchJob.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES, (
            f"ResearchJob.{col_name} must remain a JSONB-family column; "
            f"got {type_name}."
        )


def test_job_type_and_status_indexed():
    """Both job_type and status are dominant query axes; index drift
    here would silently degrade dispatcher polling."""
    job_type_col = ResearchJob.__table__.columns["job_type"]
    status_col = ResearchJob.__table__.columns["status"]
    assert job_type_col.index is True, (
        "ResearchJob.job_type must remain indexed."
    )
    assert status_col.index is True, (
        "ResearchJob.status must remain indexed."
    )


def test_status_anti_escalation_default():
    """ANTI-ESCALATION: a fresh research-job row must default to
    ``status='queued'``. A silent flip to 'completed' / 'succeeded'
    would let a dispatcher mark a job done without actually running it.
    """
    col = ResearchJob.__table__.columns["status"]
    assert col.nullable is False
    assert col.default is not None, (
        "ResearchJob.status lost its Python default — ANTI-ESCALATION DRIFT."
    )
    assert col.default.arg == "queued", (
        f"ResearchJob.status Python default drifted: expected 'queued', "
        f"got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_progress_counters_default_to_zero():
    """progress_current/progress_total must default to 0; a default of
    100 (or matching values) would let a row read as "done" without
    any work having been recorded."""
    for col_name in ("progress_current", "progress_total"):
        col = ResearchJob.__table__.columns[col_name]
        assert col.default is not None, (
            f"ResearchJob.{col_name} lost its Python default."
        )
        assert col.default.arg == 0, (
            f"ResearchJob.{col_name} default drifted: "
            f"expected 0, got {col.default.arg!r}."
        )


def test_required_identity_fields_have_no_silent_defaults():
    for col_name in ("job_type", "request_payload"):
        col = ResearchJob.__table__.columns[col_name]
        assert col.default is None, (
            f"ResearchJob.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"ResearchJob.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ResearchJob.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols  # TimestampMixin
    pk_cols = [c.name for c in ResearchJob.__table__.primary_key.columns]
    assert pk_cols == ["id"]
