"""Cycle 53 — Schema drift-lock for ``quotes`` (latest bid/ask/mid).

Pinned shape:
  * 8 business columns (1 NOT-NULL FK + 1 NOT-NULL ts + 6 nullable Numeric/String).
  * FK ``asset_id`` -> assets.id (NO ondelete cascade — quote rows must
    NOT be silently lost when an asset is reaped; if anything they should
    surface a constraint violation).
  * Composite index ``ix_quotes_asset_ts`` on (asset_id, ts) — the
    primary read pattern. Drift in column order would silently slow every
    quote-history query.
  * Numeric precision pin: bid/ask/mid/spread_abs/spread_bps all
    Numeric(18, 8) — drift here would corrupt spread-bps math used by
    downstream signal-quality checks.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Quotes are READ-ONLY for the trading path (consumed for spread-quality
      gates). assert_auto_trading_allowed() is the only auto-trading gate
      and is unchanged by this lock.
"""

from __future__ import annotations

from sqlalchemy import Numeric, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.quote import Quote


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "asset_id": (False, None, None),  # UUID FK
    "ts": (False, DateTime, None),
    "bid": (True, Numeric, None),
    "ask": (True, Numeric, None),
    "mid": (True, Numeric, None),
    "spread_abs": (True, Numeric, None),
    "spread_bps": (True, Numeric, None),
    "source": (True, String, 100),
}


NUMERIC_18_8_COLUMNS: list[str] = ["bid", "ask", "mid", "spread_abs", "spread_bps"]


def test_table_name_unchanged():
    assert Quote.__tablename__ == "quotes"


def test_business_column_set_unchanged():
    table_cols = set(Quote.__table__.columns.keys())
    # CreatedAtMixin only: subtract {id, created_at}
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"Quote missing column(s): {sorted(missing)}."
    assert not extra, f"Quote has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = Quote.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"Quote.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_pinned():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String:
            continue
        col = Quote.__table__.columns[col_name]
        assert isinstance(col.type, String), (
            f"Quote.{col_name} type drifted: expected String, got {type(col.type).__name__}."
        )
        assert col.type.length == expected_len, (
            f"Quote.{col_name} String length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_precision_18_8_unchanged():
    """Spread math depends on (18, 8). Drift would corrupt downstream bps calcs."""
    for col_name in NUMERIC_18_8_COLUMNS:
        col = Quote.__table__.columns[col_name]
        assert isinstance(col.type, Numeric), (
            f"Quote.{col_name} type drifted: expected Numeric, got {type(col.type).__name__}."
        )
        assert col.type.precision == 18, (
            f"Quote.{col_name}.precision drifted: expected 18, got {col.type.precision}."
        )
        assert col.type.scale == 8, (
            f"Quote.{col_name}.scale drifted: expected 8, got {col.type.scale}."
        )


def test_asset_id_is_uuid_fk_to_assets():
    col = Quote.__table__.columns["asset_id"]
    assert isinstance(col.type, UUID), (
        f"Quote.asset_id type drifted: expected UUID, got {type(col.type).__name__}."
    )
    fks = list(col.foreign_keys)
    assert len(fks) == 1, (
        f"Quote.asset_id FK count drifted: expected 1, got {len(fks)}."
    )
    fk = fks[0]
    assert fk.column.table.name == "assets", (
        f"Quote.asset_id FK target drifted: expected assets, got {fk.column.table.name}."
    )
    assert fk.ondelete is None, (
        f"Quote.asset_id ondelete drifted: expected None (no cascade), got {fk.ondelete!r}. "
        "Quotes must NOT be silently CASCADE-deleted with assets."
    )


def test_ts_is_timezone_aware_datetime():
    col = Quote.__table__.columns["ts"]
    assert isinstance(col.type, DateTime), (
        f"Quote.ts type drifted: expected DateTime, got {type(col.type).__name__}."
    )
    assert col.type.timezone is True, (
        "Quote.ts.timezone drifted: expected True (tz-aware)."
    )


def test_composite_index_asset_ts_unchanged():
    """ix_quotes_asset_ts(asset_id, ts) is the primary read pattern."""
    indexes = {idx.name: idx for idx in Quote.__table__.indexes}
    assert "ix_quotes_asset_ts" in indexes, (
        f"Quote composite index ix_quotes_asset_ts missing. "
        f"Found: {sorted(indexes.keys())}."
    )
    idx = indexes["ix_quotes_asset_ts"]
    cols = [c.name for c in idx.columns]
    assert cols == ["asset_id", "ts"], (
        f"Quote ix_quotes_asset_ts column order drifted: "
        f"expected ['asset_id', 'ts'], got {cols}."
    )
