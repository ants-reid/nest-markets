"""Cycle 36 — Schema drift-lock for ``news_in_decision_log`` (MH-NEWS-08-A).

Mirrors the cycle 33/34/35 schema-drift-lock pattern. Locks the
business-column set, nullability, string lengths, the four expected
indexes, and most importantly the **anti-escalation** CHECK constraint
``ck_news_in_decision_log_evidence_class_research_only`` that pins
``evidence_class = 'research_only'`` at the database layer.

If that CHECK ever silently disappears, news could be promoted from
research-only context into a trading-decision evidence class without
an explicit unlock phase — exactly the kind of silent drift this lock
is here to prevent.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection + ``pg_*`` catalog reads.
    * No imports of ``trading_control_service`` or ``BrokerService``.
"""

from __future__ import annotations

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.news_in_decision_log import NewsInDecisionLog
from app.db.session import SessionLocal


EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "decision_kind": (False, String, 32),
    "decision_id": (True, UUID, None),
    "signal_id": (True, UUID, None),
    "llm_request_log_id": (True, UUID, None),
    "news_article_id": (True, UUID, None),
    "news_item_id": (True, UUID, None),
    "evidence_class": (False, String, 32),
    "headline_snapshot": (True, String, 500),
    "source_snapshot": (True, String, 255),
    "url_snapshot": (True, String, 1000),
    "published_at_snapshot": (True, DateTime, None),
    "context_json": (True, type(None), None),  # JSONB-family — checked separately
}


JSONB_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# --------------------------------------------------------------------------- #
# Table-level invariants                                                      #
# --------------------------------------------------------------------------- #


def test_table_name_unchanged():
    assert NewsInDecisionLog.__tablename__ == "news_in_decision_log"


def test_business_column_set_unchanged():
    table_cols = set(NewsInDecisionLog.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"NewsInDecisionLog is missing column(s): {sorted(missing)}. "
        "If you intend to drop columns, ship a matrix phase + migration "
        "+ ledger entry."
    )
    assert not extra, (
        f"NewsInDecisionLog has unexpected new column(s): "
        f"{sorted(extra)}. If you intend to add columns, ship a matrix "
        "phase + migration + ledger entry and update this test."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = NewsInDecisionLog.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"NewsInDecisionLog.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}. Schema drift — "
            "ship a matrix phase + migration + ledger entry."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = NewsInDecisionLog.__table__.columns[col_name]
        assert isinstance(col.type, String), (
            f"NewsInDecisionLog.{col_name} must be String (got "
            f"{type(col.type).__name__})."
        )
        assert col.type.length == expected_len, (
            f"NewsInDecisionLog.{col_name} length drifted: expected "
            f"{expected_len}, got {col.type.length}."
        )


def test_context_json_is_jsonb_family():
    col = NewsInDecisionLog.__table__.columns["context_json"]
    type_name = type(col.type).__name__
    assert type_name in JSONB_TYPE_NAMES, (
        f"NewsInDecisionLog.context_json must remain a JSONB-family "
        f"type (got {type_name!r})."
    )


def test_evidence_class_python_default():
    """``evidence_class`` must keep its Python-side default of
    ``'research_only'`` so any future writer that omits it still
    produces an audit-only row."""
    col = NewsInDecisionLog.__table__.columns["evidence_class"]
    assert col.default is not None, (
        "NewsInDecisionLog.evidence_class must keep its Python "
        "default of 'research_only'."
    )
    assert col.default.arg == "research_only", (
        f"NewsInDecisionLog.evidence_class default drifted: expected "
        f"'research_only', got {col.default.arg!r}."
    )


def test_id_and_created_at_supplied_by_mixins():
    cols = NewsInDecisionLog.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in NewsInDecisionLog.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"


# --------------------------------------------------------------------------- #
# CHECK constraint — the anti-escalation guarantee                            #
# --------------------------------------------------------------------------- #


def test_evidence_class_research_only_check_constraint_present_in_db():
    """The MH-NEWS-08-A CHECK constraint pinning
    ``evidence_class = 'research_only'`` must exist in the live DB.

    If this constraint silently disappears, news rows could be
    promoted from research-only context into a trading-decision
    evidence class without an explicit unlock phase. That is exactly
    the kind of drift this lock exists to prevent.
    """
    with SessionLocal() as session:
        row = session.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid) AS def
                FROM pg_constraint
                WHERE conname = 'ck_news_in_decision_log_evidence_class_research_only'
                  AND conrelid = 'news_in_decision_log'::regclass
                """
            )
        ).first()
    assert row is not None, (
        "MH-NEWS-08-A CHECK constraint "
        "``ck_news_in_decision_log_evidence_class_research_only`` is "
        "missing from the live DB. This is the anti-escalation guard — "
        "do NOT drop it without an explicit unlock phase."
    )
    constraint_def = row.def_ if hasattr(row, "def_") else row[0]
    assert "research_only" in constraint_def, (
        f"CHECK constraint drifted; expected 'research_only' literal. "
        f"Got: {constraint_def!r}."
    )
    assert "evidence_class" in constraint_def, (
        f"CHECK constraint no longer references evidence_class. "
        f"Got: {constraint_def!r}."
    )


# --------------------------------------------------------------------------- #
# Index invariants                                                            #
# --------------------------------------------------------------------------- #


EXPECTED_INDEXES: dict[str, list[str]] = {
    "ix_news_in_decision_log_created_at": ["created_at"],
    "ix_news_in_decision_log_decision_kind": ["decision_kind"],
    "ix_news_in_decision_log_signal_id": ["signal_id"],
    "ix_news_in_decision_log_news_article_id": ["news_article_id"],
}


def test_expected_indexes_present_in_db():
    with SessionLocal() as session:
        rows = session.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'news_in_decision_log'
                """
            )
        ).all()
    db_indexes = {row.indexname: row.indexdef for row in rows}
    for expected_name, expected_cols in EXPECTED_INDEXES.items():
        assert expected_name in db_indexes, (
            f"MH-NEWS-08-A index {expected_name!r} is missing from "
            "the live DB. Run ``alembic upgrade head``."
        )
        indexdef = db_indexes[expected_name]
        for col in expected_cols:
            assert col in indexdef, (
                f"Index {expected_name} drifted; expected to cover "
                f"{expected_cols}. Got: {indexdef!r}."
            )
