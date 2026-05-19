"""Cycle 45 — Schema drift-lock for ``paper_validation_events`` (MH-16).

Immutable event-row table for plan lifecycle audit visibility.

Pinned shape:
  * 4 business columns + nullability + String(100) event_type
  * NOT-NULL FK paper_validation_plan_id → paper_validation_plans.id
    (indexed; an event row without a plan is meaningless)
  * ``payload`` JSONB-family
  * Required identity fields (event_type, message) carry no silent
    defaults — every event must explicitly state what happened.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text

from app.db.models.paper_validation_event import PaperValidationEvent


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "paper_validation_plan_id": (False, None, None),  # UUID FK
    "event_type": (False, String, 100),
    "message": (False, Text, None),
    "payload": (True, None, None),  # JSONB
}


def test_table_name_unchanged():
    assert PaperValidationEvent.__tablename__ == "paper_validation_events"


def test_business_column_set_unchanged():
    table_cols = set(PaperValidationEvent.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"PaperValidationEvent missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"PaperValidationEvent has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PaperValidationEvent.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PaperValidationEvent.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_event_type_string_length_unchanged():
    col = PaperValidationEvent.__table__.columns["event_type"]
    assert isinstance(col.type, String)
    assert col.type.length == 100


def test_payload_is_jsonb_family():
    col = PaperValidationEvent.__table__.columns["payload"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_plan_fk_present_and_indexed():
    col = PaperValidationEvent.__table__.columns["paper_validation_plan_id"]
    assert col.nullable is False
    assert col.index is True, (
        "PaperValidationEvent.paper_validation_plan_id must remain indexed."
    )
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "paper_validation_plans.id"


def test_required_fields_have_no_silent_defaults():
    """Every event row must explicitly state event_type and message —
    a default would let the audit timeline silently fill with empty rows."""
    for col_name in ("event_type", "message"):
        col = PaperValidationEvent.__table__.columns[col_name]
        assert col.default is None, (
            f"PaperValidationEvent.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"PaperValidationEvent.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = PaperValidationEvent.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in PaperValidationEvent.__table__.primary_key.columns]
    assert pk_cols == ["id"]
