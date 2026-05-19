"""Cycle 45 — Schema drift-lock for ``news_symbol_links``.

Many-to-many association between ``news_items`` and ``assets``.

Pinned shape:
  * 4 business columns + nullability
  * NOT-NULL CASCADE FKs: news_item_id→news_items.id, asset_id→assets.id
    (deleting a news item or asset must cascade — orphan rows would
    silently keep mentioning entities that no longer exist)
  * UNIQUE (news_item_id, asset_id) named
    ``uq_news_symbol_links_item_asset`` — a single asset cannot be
    linked to a single news item twice (would silently double-count
    relevance)
  * Numeric(10, 4) on relevance_score
  * String(100) on mention_type

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Numeric, String

from app.db.models.news_symbol_links import NewsSymbolLink


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "news_item_id": (False, None, None),  # UUID FK
    "asset_id": (False, None, None),  # UUID FK
    "relevance_score": (True, Numeric, None),
    "mention_type": (True, String, 100),
}


EXPECTED_FOREIGN_KEYS: dict[str, str] = {
    "news_item_id": "news_items.id",
    "asset_id": "assets.id",
}


def test_table_name_unchanged():
    assert NewsSymbolLink.__tablename__ == "news_symbol_links"


def test_business_column_set_unchanged():
    table_cols = set(NewsSymbolLink.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"NewsSymbolLink missing column(s): {sorted(missing)}."
    assert not extra, (
        f"NewsSymbolLink has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = NewsSymbolLink.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"NewsSymbolLink.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_relevance_score_pinned_to_10_4():
    col = NewsSymbolLink.__table__.columns["relevance_score"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 10
    assert col.type.scale == 4


def test_mention_type_string_length_unchanged():
    col = NewsSymbolLink.__table__.columns["mention_type"]
    assert isinstance(col.type, String)
    assert col.type.length == 100


def test_foreign_keys_present_with_cascade():
    """Both FKs must remain CASCADE — orphan rows would silently keep
    mentioning entities that no longer exist."""
    for col_name, expected_target in EXPECTED_FOREIGN_KEYS.items():
        col = NewsSymbolLink.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert len(fks) == 1, f"{col_name} must keep exactly one FK."
        fk = fks[0]
        assert isinstance(fk, ForeignKey)
        assert fk.target_fullname == expected_target, (
            f"NewsSymbolLink.{col_name} FK target drifted: "
            f"got {fk.target_fullname!r}."
        )
        assert (fk.ondelete or "").upper() == "CASCADE", (
            f"NewsSymbolLink.{col_name} FK ondelete must remain CASCADE; "
            f"got {fk.ondelete!r}."
        )


def test_uq_item_asset_present():
    """A single (news_item, asset) pair cannot be linked twice — would
    silently double-count relevance."""
    constraint_names = {
        c.name for c in NewsSymbolLink.__table__.constraints if c.name
    }
    assert "uq_news_symbol_links_item_asset" in constraint_names, (
        "UNIQUE (news_item_id, asset_id) constraint is missing — "
        "per-pair dedupe guarantee broken."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = NewsSymbolLink.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in NewsSymbolLink.__table__.primary_key.columns]
    assert pk_cols == ["id"]
