"""Cycle 49 — Schema drift-lock for ``ai_backtest_reports``.

AI research report generated for a strategy backtest run.
Read-only audit surface — never wired into auto-trading.

Pinned shape:
  * 10 business columns + nullability + String lengths
  * ``backtest_run_id`` is a nullable UUID with an index but
    **NO formal FK declared at the ORM layer** (locked here so
    a future commit can't silently introduce a CASCADE that
    would erase research reports when a backtest is reaped)
  * ``report_type`` defaults to ``"comparison_review"``
  * ``focus`` defaults to ``"balanced"``
  * ``status`` defaults to ``"completed"`` and is indexed
    (this is intentionally optimistic — the report is written
    only after generation; drift here would not affect trading
    but would corrupt analytics dashboards)
  * ``confidence_score`` Numeric(5, 2) (anti-precision-creep:
    confidence is a 0-100 percentage; (5,2) is exactly right)

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Numeric, String, Text

from app.db.models.ai_backtest_report import AIBacktestReport


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "backtest_run_id": (True, None, None),  # UUID indexed, NO FK
    "report_type": (False, String, 50),
    "focus": (False, String, 50),
    "status": (False, String, 50),
    "model_name": (True, String, 100),
    "input_summary": (True, None, None),  # JSONB
    "report_json": (True, None, None),  # JSONB
    "plain_english_summary": (True, Text, None),
    "confidence_score": (True, Numeric, None),
    "error_message": (True, Text, None),
}


JSONB_COLUMNS: list[str] = ["input_summary", "report_json"]


EXPECTED_DEFAULTS: dict[str, str] = {
    "report_type": "comparison_review",
    "focus": "balanced",
    "status": "completed",
}


def test_table_name_unchanged():
    assert AIBacktestReport.__tablename__ == "ai_backtest_reports"


def test_business_column_set_unchanged():
    table_cols = set(AIBacktestReport.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"AIBacktestReport missing column(s): {sorted(missing)}."
    assert not extra, (
        f"AIBacktestReport has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = AIBacktestReport.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"AIBacktestReport.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = AIBacktestReport.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_string_defaults_unchanged():
    for col_name, expected_default in EXPECTED_DEFAULTS.items():
        col = AIBacktestReport.__table__.columns[col_name]
        assert col.default is not None, f"{col_name} lost its default."
        assert col.default.arg == expected_default, (
            f"AIBacktestReport.{col_name} default drifted: "
            f"expected {expected_default!r}, got {col.default.arg!r}."
        )


def test_status_indexed():
    col = AIBacktestReport.__table__.columns["status"]
    assert col.index is True, "AIBacktestReport.status must remain indexed."


def test_backtest_run_id_indexed_but_no_fk():
    """Locked: a future commit must not silently introduce a CASCADE
    that would erase research reports when a backtest is reaped."""
    col = AIBacktestReport.__table__.columns["backtest_run_id"]
    assert col.index is True
    assert len(list(col.foreign_keys)) == 0, (
        "AIBacktestReport.backtest_run_id must remain a soft reference "
        "(no formal FK) so research reports survive backtest reaping."
    )


def test_confidence_score_pinned_to_5_2():
    """Confidence is a 0-100 percentage; (5, 2) is exactly right."""
    col = AIBacktestReport.__table__.columns["confidence_score"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 5
    assert col.type.scale == 2


def test_jsonb_columns_remain_jsonb_family():
    for col_name in JSONB_COLUMNS:
        col = AIBacktestReport.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES


def test_id_and_timestamps_supplied_by_mixins():
    cols = AIBacktestReport.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in AIBacktestReport.__table__.primary_key.columns]
    assert pk_cols == ["id"]
