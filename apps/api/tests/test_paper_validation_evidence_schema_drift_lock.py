"""Cycle 45 — Schema drift-lock for ``paper_validation_evidence`` (MH-17).

Locks the evidence-record table linking paper-execution data to a
validation plan. Read-only for execution systems; ingested manually
or via the reconciliation service only.

Pinned shape:
  * 17 business columns + nullability + String lengths
  * NOT-NULL FK paper_validation_plan_id → paper_validation_plans.id
    (indexed; evidence without a plan is meaningless)
  * Numeric pins: entry_price/exit_price/pnl_amount=(18,8);
    pnl_pct=(12,6); r_multiple=(10,4)
  * **DEFAULT GUARDS**:
      - ``confidence`` defaults to ``'manual'`` (not 'high' — drift to
        'high' would let unverified evidence be silently treated as
        high-confidence)
      - ``result`` defaults to ``'unknown'`` (not 'win' — drift to
        'win' would silently inflate validation metrics)
      - ``included_in_metrics`` defaults to ``True`` at BOTH Python
        and server_default layers (intentional — every evidence row
        defaults to counting; this lock prevents an accidental flip
        to False that would silently exclude evidence from metrics)

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text

from app.db.models.paper_validation_evidence import PaperValidationEvidence


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "paper_validation_plan_id": (False, None, None),  # UUID FK
    "source_type": (False, String, 50),
    "source_id": (True, None, None),  # UUID
    "confidence": (False, String, 20),
    "asset": (True, String, 50),
    "timeframe": (True, String, 10),
    "side": (True, String, 20),
    "opened_at": (True, DateTime, None),
    "closed_at": (True, DateTime, None),
    "entry_price": (True, Numeric, None),
    "exit_price": (True, Numeric, None),
    "pnl_amount": (True, Numeric, None),
    "pnl_pct": (True, Numeric, None),
    "r_multiple": (True, Numeric, None),
    "result": (False, String, 20),
    "payload": (True, None, None),  # JSONB
    "notes": (True, Text, None),
    "included_in_metrics": (False, Boolean, None),
}


PINNED_NUMERIC: list[tuple[str, int, int]] = [
    ("entry_price", 18, 8),
    ("exit_price", 18, 8),
    ("pnl_amount", 18, 8),
    ("pnl_pct", 12, 6),
    ("r_multiple", 10, 4),
]


def test_table_name_unchanged():
    assert PaperValidationEvidence.__tablename__ == "paper_validation_evidence"


def test_business_column_set_unchanged():
    table_cols = set(PaperValidationEvidence.__table__.columns.keys())
    # TimestampMixin
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"PaperValidationEvidence missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"PaperValidationEvidence has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PaperValidationEvidence.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PaperValidationEvidence.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = PaperValidationEvidence.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"PaperValidationEvidence.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_precision_unchanged():
    for col_name, expected_precision, expected_scale in PINNED_NUMERIC:
        col = PaperValidationEvidence.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == expected_precision, (
            f"PaperValidationEvidence.{col_name} precision drifted: "
            f"expected {expected_precision}, got {col.type.precision}."
        )
        assert col.type.scale == expected_scale, (
            f"PaperValidationEvidence.{col_name} scale drifted: "
            f"expected {expected_scale}, got {col.type.scale}."
        )


def test_payload_is_jsonb_family():
    col = PaperValidationEvidence.__table__.columns["payload"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_plan_fk_present_and_indexed():
    col = PaperValidationEvidence.__table__.columns["paper_validation_plan_id"]
    assert col.nullable is False
    assert col.index is True
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "paper_validation_plans.id"


def test_confidence_default_manual_anti_escalation():
    """ANTI-ESCALATION: confidence defaults to 'manual' (low-trust).
    Drift to 'high' would let unverified evidence be silently treated
    as high-confidence."""
    col = PaperValidationEvidence.__table__.columns["confidence"]
    assert col.default is not None
    assert col.default.arg == "manual", (
        f"PaperValidationEvidence.confidence default drifted: "
        f"expected 'manual', got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_result_default_unknown_anti_escalation():
    """ANTI-ESCALATION: result defaults to 'unknown'. Drift to 'win'
    would silently inflate validation metrics."""
    col = PaperValidationEvidence.__table__.columns["result"]
    assert col.default is not None
    assert col.default.arg == "unknown", (
        f"PaperValidationEvidence.result default drifted: "
        f"expected 'unknown', got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_included_in_metrics_default_true_both_layers():
    """Pinned default: included_in_metrics=True at BOTH Python and
    server_default layers. A flip to False would silently exclude
    evidence from validation metrics."""
    col = PaperValidationEvidence.__table__.columns["included_in_metrics"]
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg is True, (
        f"PaperValidationEvidence.included_in_metrics Python default drifted: "
        f"expected True, got {col.default.arg!r}."
    )
    assert col.server_default is not None, (
        "PaperValidationEvidence.included_in_metrics lost its server_default."
    )
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "true" in str(server_default_value).lower(), (
        f"PaperValidationEvidence.included_in_metrics server_default drifted: "
        f"got {server_default_value!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = PaperValidationEvidence.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in PaperValidationEvidence.__table__.primary_key.columns]
    assert pk_cols == ["id"]
