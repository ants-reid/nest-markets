"""Cycle 47 — Schema drift-lock for ``filing_events``.

SEC filings and earnings events. Provider-fed; never written by
auto-trading code. Read-only data feed.

Pinned shape:
  * 5 business columns + nullability + String(512) filing_url
  * UNIQUE (asset_id, event_type, event_date) named
    ``uq_filing_events_asset_type_date`` — per-asset/type/date dedupe;
    drift would silently double-count earnings events
  * NOT-NULL CASCADE FK asset_id → assets.id (a deleted asset must
    cascade — orphan filings would silently mention a missing asset)
  * ``event_type`` non-null Enum
  * JSONB-family ``extra_metadata``

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Date, ForeignKey, String

from app.db.models.filing_events import FilingEvent


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "asset_id": (False, None, None),  # UUID FK CASCADE
    "event_type": (False, None, None),  # Enum
    "event_date": (False, Date, None),
    "filing_url": (True, String, 512),
    "extra_metadata": (True, None, None),  # JSONB
}


def test_table_name_unchanged():
    assert FilingEvent.__tablename__ == "filing_events"


def test_business_column_set_unchanged():
    table_cols = set(FilingEvent.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"FilingEvent missing column(s): {sorted(missing)}."
    assert not extra, f"FilingEvent has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = FilingEvent.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"FilingEvent.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_filing_url_string_length_unchanged():
    col = FilingEvent.__table__.columns["filing_url"]
    assert isinstance(col.type, String)
    assert col.type.length == 512


def test_asset_fk_cascade():
    """Orphan filings would silently mention a deleted asset."""
    col = FilingEvent.__table__.columns["asset_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "assets.id"
    assert (fk.ondelete or "").upper() == "CASCADE", (
        f"FilingEvent.asset_id ondelete must remain CASCADE; got {fk.ondelete!r}."
    )


def test_uq_asset_type_date_present():
    """Per-asset/type/date dedupe; drift would silently double-count."""
    constraint_names = {c.name for c in FilingEvent.__table__.constraints if c.name}
    assert "uq_filing_events_asset_type_date" in constraint_names


def test_extra_metadata_is_jsonb_family():
    col = FilingEvent.__table__.columns["extra_metadata"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES


def test_id_and_timestamps_supplied_by_mixins():
    cols = FilingEvent.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in FilingEvent.__table__.primary_key.columns]
    assert pk_cols == ["id"]
