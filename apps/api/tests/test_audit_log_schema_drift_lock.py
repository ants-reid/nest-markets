"""Cycle 43 — Schema drift-lock for ``audit_logs``.

Locks the generic event-audit trail. Pure additive append-only table.

Pinned shape:
  * 4 business columns + nullability + String(100) lengths on
    entity_type / event_type
  * ``payload_json`` JSONB-family
  * Required fields (entity_type, event_type) carry no silent
    defaults — every audit row must explicitly state what happened
    and to what kind of entity.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import String

from app.db.models.audit_log import AuditLog


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "entity_type": (False, String, 100),
    "entity_id": (True, None, None),  # UUID
    "event_type": (False, String, 100),
    "payload_json": (True, None, None),  # JSONB
}


def test_table_name_unchanged():
    assert AuditLog.__tablename__ == "audit_logs"


def test_business_column_set_unchanged():
    table_cols = set(AuditLog.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"AuditLog is missing column(s): {sorted(missing)}."
    assert not extra, f"AuditLog has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = AuditLog.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"AuditLog.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = AuditLog.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"AuditLog.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_payload_json_is_jsonb_family():
    col = AuditLog.__table__.columns["payload_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES, (
        f"AuditLog.payload_json must remain a JSONB-family column; "
        f"got {type_name}."
    )


def test_required_fields_have_no_silent_defaults():
    """entity_type and event_type must NOT gain Python or server
    defaults. A default 'unknown' or 'misc' would let an audit row be
    written without the caller specifying what actually happened.
    """
    for col_name in ("entity_type", "event_type"):
        col = AuditLog.__table__.columns[col_name]
        assert col.default is None, (
            f"AuditLog.{col_name} gained a Python default — silent "
            "defaults on audit identity fields would mask audit-quality drift."
        )
        assert col.server_default is None, (
            f"AuditLog.{col_name} gained a server_default — same concern."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = AuditLog.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in AuditLog.__table__.primary_key.columns]
    assert pk_cols == ["id"]
