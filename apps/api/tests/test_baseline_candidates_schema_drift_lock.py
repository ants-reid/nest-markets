"""Cycle 50 — Schema drift-lock for ``baseline_candidates``.

Research-stage baseline candidate from strategy lab results.
**Explicitly NOT an activation or live approval** — this is the
research-only intake layer.

Pinned shape:
  * 12 business columns + nullability + String lengths
  * 3 soft-reference UUID columns (backtest_run_id /
    strategy_config_id / ai_backtest_report_id) — all nullable,
    indexed, and **NO formal FK** at ORM layer (locked so a
    future commit can't introduce a CASCADE that would erase
    candidate research records when source artefacts are reaped).
  * 3 NOT-NULL indexed identifier columns: asset / timeframe /
    strategy_type (used by candidate-discovery dashboards).
  * 2 NOT-NULL JSONB columns with empty-dict defaults
    (parameters / metrics) — anti-misfire so a NULL doesn't get
    silently treated as "no parameters" when ranking candidates.
  * ``status`` defaults to ``"watchlist_candidate"`` and is
    indexed — **anti-promotion**: drift to "activated" or
    "promoted" or "approved" would silently move new candidates
    into a state that could be picked up by a future
    activation-wiring layer.
  * ``reviewed_at`` is timezone-aware nullable (a candidate may
    not yet have been reviewed).

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, String, Text

from app.db.models.baseline_candidate import BaselineCandidate


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "backtest_run_id": (True, None, None),  # UUID indexed, NO FK
    "strategy_config_id": (True, None, None),  # UUID indexed, NO FK
    "ai_backtest_report_id": (True, None, None),  # UUID indexed, NO FK
    "asset": (False, String, 50),
    "timeframe": (False, String, 10),
    "strategy_type": (False, String, 100),
    "parameters": (False, None, None),  # JSONB
    "metrics": (False, None, None),  # JSONB
    "status": (False, String, 50),
    "review_notes": (True, Text, None),
    "created_by": (True, String, 255),
    "reviewed_by": (True, String, 255),
    "reviewed_at": (True, DateTime, None),
}


SOFT_REF_UUID_COLUMNS: list[str] = [
    "backtest_run_id", "strategy_config_id", "ai_backtest_report_id",
]


INDEXED_IDENTIFIER_COLUMNS: list[str] = ["asset", "timeframe", "strategy_type", "status"]


JSONB_NOT_NULL_DICT_COLUMNS: list[str] = ["parameters", "metrics"]


def test_table_name_unchanged():
    assert BaselineCandidate.__tablename__ == "baseline_candidates"


def test_business_column_set_unchanged():
    table_cols = set(BaselineCandidate.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"BaselineCandidate missing column(s): {sorted(missing)}."
    assert not extra, (
        f"BaselineCandidate has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = BaselineCandidate.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"BaselineCandidate.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = BaselineCandidate.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_soft_ref_uuids_indexed_but_no_fk():
    """Locked: a future commit must not introduce a CASCADE that would
    erase candidate research records when source artefacts are reaped."""
    for col_name in SOFT_REF_UUID_COLUMNS:
        col = BaselineCandidate.__table__.columns[col_name]
        assert col.index is True, f"{col_name} must remain indexed."
        assert len(list(col.foreign_keys)) == 0, (
            f"BaselineCandidate.{col_name} must remain a soft reference "
            "(no formal FK)."
        )


def test_identifier_columns_indexed():
    for col_name in INDEXED_IDENTIFIER_COLUMNS:
        col = BaselineCandidate.__table__.columns[col_name]
        assert col.index is True, (
            f"BaselineCandidate.{col_name} must remain indexed for "
            "candidate-discovery dashboards."
        )


def test_jsonb_not_null_dict_default():
    """Anti-misfire so a NULL doesn't get silently treated as 'no
    parameters' when ranking candidates."""
    for col_name in JSONB_NOT_NULL_DICT_COLUMNS:
        col = BaselineCandidate.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES
        assert col.nullable is False
        assert col.default is not None
        default_value = col.default.arg
        if callable(default_value):
            default_value = default_value({})
        assert default_value == {}, (
            f"BaselineCandidate.{col_name} default drifted from empty dict; "
            f"got {default_value!r}."
        )


def test_status_default_is_watchlist_candidate():
    """Anti-promotion: drift to 'activated'/'promoted'/'approved' would
    silently move new candidates into a state that could be picked up by
    a future activation-wiring layer."""
    col = BaselineCandidate.__table__.columns["status"]
    assert col.default is not None
    assert col.default.arg == "watchlist_candidate", (
        f"BaselineCandidate.status default drifted: "
        f"expected 'watchlist_candidate', got {col.default.arg!r}."
    )


def test_reviewed_at_is_timezone_aware():
    col = BaselineCandidate.__table__.columns["reviewed_at"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True


def test_id_and_timestamps_supplied_by_mixins():
    cols = BaselineCandidate.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in BaselineCandidate.__table__.primary_key.columns]
    assert pk_cols == ["id"]
