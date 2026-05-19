"""Cycle 42 — Schema drift-lock for ``incident_logs`` (MH-MON-05).

Locks the append-only operational/safety incident log. Pure additive
table — no production code path consumes it for control decisions.

Pinned shape:
  * 8 business columns, full nullability map
  * String lengths (severity=16, code=80, title=255, source=64,
    correlation_id=100)
  * ``extra_json`` JSONB-family
  * No defaults pinned: writers must explicitly supply severity, code,
    title, source — silent defaults here would mask incident-quality
    drift.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import String, Text

from app.db.models.incident_log import IncidentLog


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "severity": (False, String, 16),
    "code": (False, String, 80),
    "title": (False, String, 255),
    "detail": (True, Text, None),
    "source": (False, String, 64),
    "extra_json": (True, None, None),  # JSONB
    "correlation_id": (True, String, 100),
    "occurred_at": (True, None, None),  # DateTime (declared without explicit type class)
}


def test_table_name_unchanged():
    assert IncidentLog.__tablename__ == "incident_logs"


def test_business_column_set_unchanged():
    table_cols = set(IncidentLog.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"IncidentLog is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"IncidentLog has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = IncidentLog.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"IncidentLog.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = IncidentLog.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"IncidentLog.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_extra_json_is_jsonb_family():
    col = IncidentLog.__table__.columns["extra_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES, (
        f"IncidentLog.extra_json must remain a JSONB-family column; "
        f"got {type_name}."
    )


def test_required_columns_have_no_defaults():
    """Severity/code/title/source must NOT gain silent defaults.
    A default-'info' severity, for example, would let a critical
    incident be silently downgraded.
    """
    for col_name in ("severity", "code", "title", "source"):
        col = IncidentLog.__table__.columns[col_name]
        assert col.default is None, (
            f"IncidentLog.{col_name} gained a Python default — silent "
            "defaults on required incident fields would mask "
            "incident-quality drift."
        )
        assert col.server_default is None, (
            f"IncidentLog.{col_name} gained a server_default — same "
            "concern."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = IncidentLog.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in IncidentLog.__table__.primary_key.columns]
    assert pk_cols == ["id"]
