"""Cycle 45 — Schema drift-lock for ``paper_validation_plans`` (MH-16).

Locks the validation-gate plan table linking baseline candidates to
paper-proof requirements.

Pinned shape:
  * 17 business columns + nullability + String lengths
  * 4 indexed cols: baseline_candidate_id, backtest_run_id,
    strategy_config_id, status
  * Numeric pins: target_profit_factor / max_drawdown_pct /
    max_daily_loss_pct = (12, 6); starting_paper_capital = (18, 4)
  * 4 JSONB-family payload columns
  * **ANTI-ESCALATION**: ``status`` defaults to ``'pending'`` (a
    silent 'passed' would let a baseline auto-clear the validation
    gate without any paper proof)
  * Pinned validation thresholds: required_trades=100, minimum_days=30,
    starting_paper_capital=200000 — drift here would silently weaken
    the validation bar.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Integer, Numeric, String, Text

from app.db.models.paper_validation_plan import PaperValidationPlan


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "baseline_candidate_id": (False, None, None),  # UUID
    "backtest_run_id": (True, None, None),  # UUID
    "strategy_config_id": (True, None, None),  # UUID
    "status": (False, String, 50),
    "required_trades": (False, Integer, None),
    "minimum_days": (False, Integer, None),
    "target_profit_factor": (True, Numeric, None),
    "max_drawdown_pct": (True, Numeric, None),
    "max_daily_loss_pct": (True, Numeric, None),
    "starting_paper_capital": (False, Numeric, None),
    "backtest_metrics": (True, None, None),  # JSONB
    "paper_metrics": (True, None, None),  # JSONB
    "progress": (True, None, None),  # JSONB
    "pass_fail_reasons": (True, None, None),  # JSONB
    "started_at": (True, DateTime, None),
    "completed_at": (True, DateTime, None),
    "created_by": (True, String, 255),
    "reviewed_by": (True, String, 255),
    "review_notes": (True, Text, None),
}


PINNED_NUMERIC: list[tuple[str, int, int]] = [
    ("target_profit_factor", 12, 6),
    ("max_drawdown_pct", 12, 6),
    ("max_daily_loss_pct", 12, 6),
    ("starting_paper_capital", 18, 4),
]


JSONB_COLUMNS: list[str] = [
    "backtest_metrics",
    "paper_metrics",
    "progress",
    "pass_fail_reasons",
]


INDEXED_COLUMNS: list[str] = [
    "baseline_candidate_id",
    "backtest_run_id",
    "strategy_config_id",
    "status",
]


def test_table_name_unchanged():
    assert PaperValidationPlan.__tablename__ == "paper_validation_plans"


def test_business_column_set_unchanged():
    table_cols = set(PaperValidationPlan.__table__.columns.keys())
    # TimestampMixin → created_at + updated_at
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"PaperValidationPlan missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"PaperValidationPlan has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PaperValidationPlan.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PaperValidationPlan.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = PaperValidationPlan.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"PaperValidationPlan.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_precision_unchanged():
    for col_name, expected_precision, expected_scale in PINNED_NUMERIC:
        col = PaperValidationPlan.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision
        assert col.type.scale == expected_scale, (
            f"PaperValidationPlan.{col_name} scale drifted: "
            f"expected {expected_scale}, got {col.type.scale}."
        )


def test_jsonb_columns_remain_jsonb_family():
    for col_name in JSONB_COLUMNS:
        col = PaperValidationPlan.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES, (
            f"PaperValidationPlan.{col_name} must remain JSONB-family; "
            f"got {type_name}."
        )


def test_indexed_columns_remain_indexed():
    for col_name in INDEXED_COLUMNS:
        col = PaperValidationPlan.__table__.columns[col_name]
        assert col.index is True, (
            f"PaperValidationPlan.{col_name} must remain indexed (index=True)."
        )


def test_status_anti_escalation_default():
    """ANTI-ESCALATION: a fresh plan must default to ``status='pending'``.
    A silent 'passed'/'approved' would let a baseline auto-clear the
    validation gate without any paper proof."""
    col = PaperValidationPlan.__table__.columns["status"]
    assert col.nullable is False
    assert col.default is not None, (
        "PaperValidationPlan.status lost its Python default — ANTI-ESCALATION DRIFT."
    )
    assert col.default.arg == "pending", (
        f"PaperValidationPlan.status default drifted: expected 'pending', "
        f"got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_validation_thresholds_pinned():
    """Pinned validation thresholds. Drift here would silently weaken
    the validation bar (e.g. required_trades=10 instead of 100)."""
    rt_col = PaperValidationPlan.__table__.columns["required_trades"]
    assert rt_col.default is not None
    assert rt_col.default.arg == 100, (
        f"PaperValidationPlan.required_trades default drifted: "
        f"expected 100, got {rt_col.default.arg!r}. Validation bar weakened."
    )

    md_col = PaperValidationPlan.__table__.columns["minimum_days"]
    assert md_col.default is not None
    assert md_col.default.arg == 30, (
        f"PaperValidationPlan.minimum_days default drifted: "
        f"expected 30, got {md_col.default.arg!r}. Validation bar weakened."
    )

    cap_col = PaperValidationPlan.__table__.columns["starting_paper_capital"]
    assert cap_col.default is not None
    assert cap_col.default.arg == 200000, (
        f"PaperValidationPlan.starting_paper_capital default drifted: "
        f"expected 200000, got {cap_col.default.arg!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = PaperValidationPlan.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in PaperValidationPlan.__table__.primary_key.columns]
    assert pk_cols == ["id"]
