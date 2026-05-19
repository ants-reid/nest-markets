"""Cycle 42 — Schema drift-lock for ``news_articles``.

Locks the normalized news-article store (MH-NEWS-02). With MH-NEWS-04
(News Risk advisory flag) still pending, this is the dependency
surface every future news-consumer must respect.

Pinned shape:
  * 14 business columns, full nullability map, String lengths
  * 5 JSONB-family payload columns
  * ``provider_article_id`` UNIQUE (dedupe guarantee — a single article
    cannot be ingested twice and silently double-count)
  * ``ix_news_articles_published_at`` index present
  * **ANTI-ESCALATION**: ``evidence_class`` defaults to
    ``'research_only'`` at both Python and server_default layers and
    is NOT NULL — news must never default to a higher-trust evidence
    class without an explicit unlock phase. (Drift-lock rule 13.)

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import DateTime, String, Text

from app.db.models.news_article import NewsArticle


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "provider_article_id": (True, String, 255),
    "published_at": (False, DateTime, None),
    "headline": (False, String, 500),
    "summary": (True, Text, None),
    "body_text": (True, Text, None),
    "source_name": (True, String, 255),
    "url": (True, String, 1000),
    "authors_json": (True, None, None),  # JSONB
    "tickers_json": (True, None, None),  # JSONB
    "sector_tags_json": (True, None, None),  # JSONB
    "sentiment_provider": (True, String, 100),
    "raw_json": (True, None, None),  # JSONB
    "citations_json": (True, None, None),  # JSONB
    "evidence_class": (False, String, 32),
}


JSONB_COLUMNS: list[str] = [
    "authors_json",
    "tickers_json",
    "sector_tags_json",
    "raw_json",
    "citations_json",
]


def test_table_name_unchanged():
    assert NewsArticle.__tablename__ == "news_articles"


def test_business_column_set_unchanged():
    table_cols = set(NewsArticle.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"NewsArticle is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"NewsArticle has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = NewsArticle.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"NewsArticle.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = NewsArticle.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"NewsArticle.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_jsonb_columns_remain_jsonb_family():
    for col_name in JSONB_COLUMNS:
        col = NewsArticle.__table__.columns[col_name]
        type_name = type(col.type).__name__
        assert type_name in JSON_TYPE_NAMES, (
            f"NewsArticle.{col_name} must remain a JSONB-family column; "
            f"got {type_name}."
        )


def test_provider_article_id_is_unique():
    """Dedupe guarantee: a single article must not be ingested twice
    and silently double-count downstream news-aware consumers."""
    col = NewsArticle.__table__.columns["provider_article_id"]
    assert col.unique is True, (
        "NewsArticle.provider_article_id must remain UNIQUE."
    )


def test_published_at_index_present():
    indexes_by_name = {idx.name: idx for idx in NewsArticle.__table__.indexes}
    assert "ix_news_articles_published_at" in indexes_by_name, (
        "ORM-declared index ix_news_articles_published_at is missing."
    )


def test_evidence_class_anti_escalation_default():
    """ANTI-ESCALATION GUARANTEE (drift-lock rule 13): every news row
    must default to ``evidence_class='research_only'`` at BOTH Python
    and server_default layers. A silent flip to a higher-trust
    evidence class would let news escalate into a trading-decision
    input without an explicit unlock phase.
    """
    col = NewsArticle.__table__.columns["evidence_class"]
    assert col.nullable is False, (
        "NewsArticle.evidence_class must remain NOT NULL — "
        "ANTI-ESCALATION GUARANTEE."
    )
    assert col.default is not None, (
        "NewsArticle.evidence_class lost its Python default — "
        "ANTI-ESCALATION DRIFT."
    )
    assert col.default.arg == "research_only", (
        f"NewsArticle.evidence_class Python default drifted: "
        f"expected 'research_only', got {col.default.arg!r}. "
        "ANTI-ESCALATION DRIFT."
    )
    assert col.server_default is not None
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "research_only" in str(server_default_value), (
        f"NewsArticle.evidence_class server_default drifted: "
        f"got {server_default_value!r}. ANTI-ESCALATION DRIFT."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = NewsArticle.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in NewsArticle.__table__.primary_key.columns]
    assert pk_cols == ["id"]
