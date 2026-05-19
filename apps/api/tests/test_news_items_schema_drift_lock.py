"""Cycle 45 — Schema drift-lock for ``news_items``.

Sibling of cycle-42 ``news_articles``; locks the alternate
provider-news-storage table (older shape kept for backwards-compat
ingest paths).

Pinned shape:
  * 11 business columns + nullability + String lengths
  * UNIQUE (external_id, source) named ``uq_news_items_external_source``
    — dedupe guarantee per provider stream
  * Index ``ix_news_items_published_at``
  * Numeric(10, 4) on sentiment_score / urgency_score
  * ``extra_metadata`` JSONB-family
  * Required fields (headline, published_at) carry no silent defaults.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Numeric, String, Text

from app.db.models.news_items import NewsItem


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "external_id": (True, String, 512),
    "headline": (False, Text, None),
    "summary": (True, Text, None),
    "full_text": (True, Text, None),
    "source": (True, String, 100),
    "published_at": (False, DateTime, None),
    "ingested_at": (True, DateTime, None),
    "sentiment_score": (True, Numeric, None),
    "urgency_score": (True, Numeric, None),
    "url": (True, String, 512),
    "extra_metadata": (True, None, None),  # JSONB
}


PINNED_NUMERIC_10_4: list[str] = ["sentiment_score", "urgency_score"]


def test_table_name_unchanged():
    assert NewsItem.__tablename__ == "news_items"


def test_business_column_set_unchanged():
    table_cols = set(NewsItem.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"NewsItem missing column(s): {sorted(missing)}."
    assert not extra, f"NewsItem has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = NewsItem.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"NewsItem.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = NewsItem.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"NewsItem.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = NewsItem.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"NewsItem.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_columns_pinned_to_10_4():
    for col_name in PINNED_NUMERIC_10_4:
        col = NewsItem.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 4, (
            f"NewsItem.{col_name} scale drifted: expected 4, got {col.type.scale}."
        )


def test_extra_metadata_is_jsonb_family():
    col = NewsItem.__table__.columns["extra_metadata"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_uq_external_source_present():
    """Per-provider dedupe guarantee."""
    constraint_names = {c.name for c in NewsItem.__table__.constraints if c.name}
    assert "uq_news_items_external_source" in constraint_names, (
        "UNIQUE (external_id, source) constraint is missing — "
        "per-provider dedupe guarantee broken."
    )


def test_published_at_index_present():
    indexes_by_name = {idx.name: idx for idx in NewsItem.__table__.indexes}
    assert "ix_news_items_published_at" in indexes_by_name, (
        "Index ix_news_items_published_at is missing."
    )


def test_required_fields_have_no_silent_defaults():
    for col_name in ("headline", "published_at"):
        col = NewsItem.__table__.columns[col_name]
        assert col.default is None, (
            f"NewsItem.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"NewsItem.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = NewsItem.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in NewsItem.__table__.primary_key.columns]
    assert pk_cols == ["id"]
