"""Cycle 36 — Schema drift-lock for ``llm_request_logs`` (MH-150).

Mirrors the cycle 33/34/35 schema-drift-lock pattern. Locks the
business-column set, nullability, string lengths, and the three
expected indexes installed by the MH-150 migration.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection + ``pg_indexes`` catalog reads.
    * No imports of ``trading_control_service`` or ``BrokerService``.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.llm_request_log import LLMRequestLog
from app.db.session import SessionLocal


# Ship state — column → (nullable, expected SQLAlchemy type class, optional length).
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "provider": (False, String, 50),
    "model_requested": (False, String, 100),
    "model_returned": (True, String, 100),
    "system_prompt_hash": (True, String, 64),
    "user_prompt_hash": (True, String, 64),
    "system_prompt_preview": (True, Text, None),
    "user_prompt_preview": (True, Text, None),
    "prompt_version_id": (True, UUID, None),
    "response_payload_json": (True, type(None), None),  # JSONB-family — checked separately
    "stop_reason": (True, String, 50),
    "prompt_tokens": (True, Integer, None),
    "completion_tokens": (True, Integer, None),
    "total_tokens": (True, Integer, None),
    "latency_ms": (True, Integer, None),
    "error_class": (True, String, 100),
    "error_message": (True, Text, None),
    "correlation_id": (True, String, 100),
    "started_at": (True, type(None), None),  # DateTime — checked separately
}


JSONB_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# --------------------------------------------------------------------------- #
# Table-level invariants                                                      #
# --------------------------------------------------------------------------- #


def test_table_name_unchanged():
    assert LLMRequestLog.__tablename__ == "llm_request_logs"


def test_business_column_set_unchanged():
    table_cols = set(LLMRequestLog.__table__.columns.keys())
    # CreatedAtMixin + UUIDPrimaryKeyMixin contribute id/created_at.
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"LLMRequestLog is missing column(s): {sorted(missing)}. If you "
        "intend to drop columns, ship a matrix phase + migration + "
        "ledger entry."
    )
    assert not extra, (
        f"LLMRequestLog has unexpected new column(s): {sorted(extra)}. "
        "If you intend to add columns, ship a matrix phase + migration "
        "+ ledger entry and update this test."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = LLMRequestLog.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"LLMRequestLog.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}. Schema drift — "
            "ship a matrix phase + migration + ledger entry."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = LLMRequestLog.__table__.columns[col_name]
        assert isinstance(col.type, String), (
            f"LLMRequestLog.{col_name} must be String (got "
            f"{type(col.type).__name__})."
        )
        assert col.type.length == expected_len, (
            f"LLMRequestLog.{col_name} length drifted: expected "
            f"{expected_len}, got {col.type.length}."
        )


def test_response_payload_json_is_jsonb_family():
    col = LLMRequestLog.__table__.columns["response_payload_json"]
    type_name = type(col.type).__name__
    assert type_name in JSONB_TYPE_NAMES, (
        f"LLMRequestLog.response_payload_json must remain a JSONB-family "
        f"type (got {type_name!r})."
    )


def test_id_and_created_at_supplied_by_mixins():
    cols = LLMRequestLog.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in LLMRequestLog.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"


# --------------------------------------------------------------------------- #
# Index invariants (asserted via pg_indexes — they are installed by the      #
# migration with op.create_index, not by the ORM)                            #
# --------------------------------------------------------------------------- #


EXPECTED_INDEXES: dict[str, list[str]] = {
    "ix_llm_request_logs_created_at": ["created_at"],
    "ix_llm_request_logs_correlation_id": ["correlation_id"],
    "ix_llm_request_logs_provider_model": ["provider", "model_requested"],
}


def test_expected_indexes_present_in_db():
    with SessionLocal() as session:
        rows = session.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'llm_request_logs'
                """
            )
        ).all()
    db_indexes = {row.indexname: row.indexdef for row in rows}
    for expected_name, expected_cols in EXPECTED_INDEXES.items():
        assert expected_name in db_indexes, (
            f"MH-150 index {expected_name!r} is missing from the live "
            "DB. Run ``alembic upgrade head``."
        )
        indexdef = db_indexes[expected_name]
        for col in expected_cols:
            assert col in indexdef, (
                f"Index {expected_name} drifted; expected to cover "
                f"{expected_cols}. Got: {indexdef!r}."
            )
