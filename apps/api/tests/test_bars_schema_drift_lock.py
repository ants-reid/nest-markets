"""Cycle 51 — Schema drift-lock for ``bars``.

OHLCV bar history — the highest-volume table in the system and
the raw substrate every backtest, scoring, and feature pipeline
ultimately reads from. Read-only for the trading path.

Pinned shape:
  * 9 business columns + nullability + String lengths
  * UNIQUE constraint ``uq_bars_asset_timeframe_ts`` on
    (asset_id, timeframe, ts) — drift would let two bar rows
    share the same point in time and silently double-count
    every range query (corrupting every downstream feature
    and PnL calc).
  * Composite index ``ix_bars_asset_timeframe_ts`` on the same
    triple — drift would silently turn every range scan into a
    full table scan.
  * FK ``asset_id → assets.id`` (no explicit ondelete; defaults
    to NO ACTION — locked here so a future commit can't
    introduce a CASCADE that would erase every bar of an asset
    that gets soft-deleted from the universe).
  * **OHLC + VWAP all Numeric(18, 8)** — required precision for
    FX and crypto pairs (sub-cent tick resolution).
  * **Volume Numeric(22, 8)** — note the **wider precision**
    (22 not 18) because crypto/FX volumes can be very large
    (locked because a drift to (18, 8) would silently overflow
    high-volume sessions and crash inserts).
  * ``ts`` NOT-NULL timezone-aware (bar timestamps must remain
    canonical UTC).

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric, String

from app.db.models.bar import Bar


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "asset_id": (False, None, None),  # UUID FK
    "timeframe": (False, String, 10),
    "ts": (False, DateTime, None),
    "open": (False, Numeric, None),
    "high": (False, Numeric, None),
    "low": (False, Numeric, None),
    "close": (False, Numeric, None),
    "volume": (True, Numeric, None),
    "vwap": (True, Numeric, None),
    "source": (True, String, 100),
}


PINNED_NUMERIC_18_8: list[str] = ["open", "high", "low", "close", "vwap"]


def test_table_name_unchanged():
    assert Bar.__tablename__ == "bars"


def test_business_column_set_unchanged():
    table_cols = set(Bar.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"Bar missing column(s): {sorted(missing)}."
    assert not extra, f"Bar has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = Bar.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"Bar.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = Bar.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_ohlc_vwap_pinned_to_18_8():
    """Required precision for FX and crypto pairs (sub-cent ticks)."""
    for col_name in PINNED_NUMERIC_18_8:
        col = Bar.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 18, (
            f"Bar.{col_name} precision drifted: expected 18, got {col.type.precision}."
        )
        assert col.type.scale == 8


def test_volume_pinned_to_22_8():
    """Wider precision than OHLC because crypto/FX volumes can be very
    large; a drift to (18, 8) would silently overflow high-volume
    sessions and crash inserts."""
    col = Bar.__table__.columns["volume"]
    assert isinstance(col.type, Numeric)
    assert col.type.precision == 22, (
        f"Bar.volume precision drifted: expected 22, got {col.type.precision}."
    )
    assert col.type.scale == 8


def test_asset_fk_target_and_no_cascade():
    """Locked: a future commit must not introduce a CASCADE that would
    erase every bar of an asset that gets soft-deleted."""
    col = Bar.__table__.columns["asset_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "assets.id"
    # ondelete must remain unset (NO ACTION default)
    assert fk.ondelete is None or fk.ondelete.upper() == "NO ACTION", (
        f"Bar.asset_id FK ondelete drifted: got {fk.ondelete!r}; expected default."
    )


def test_ts_is_timezone_aware():
    col = Bar.__table__.columns["ts"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True, (
        "Bar.ts must remain timezone-aware — bar timestamps must "
        "stay canonical UTC."
    )


def test_unique_constraint_present():
    """Drift would let two bar rows share the same point in time and
    silently double-count every range query."""
    uqs = [
        c for c in Bar.__table__.constraints
        if type(c).__name__ == "UniqueConstraint"
    ]
    names = {uq.name for uq in uqs}
    assert "uq_bars_asset_timeframe_ts" in names, (
        f"UNIQUE uq_bars_asset_timeframe_ts missing; got {sorted(names)}."
    )


def test_composite_index_present():
    """Drift would silently turn every range scan into a full table scan."""
    indexes_by_name = {idx.name: idx for idx in Bar.__table__.indexes}
    assert "ix_bars_asset_timeframe_ts" in indexes_by_name
    idx = indexes_by_name["ix_bars_asset_timeframe_ts"]
    col_names = [c.name for c in idx.columns]
    assert col_names == ["asset_id", "timeframe", "ts"], (
        f"ix_bars_asset_timeframe_ts column order drifted: got {col_names}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = Bar.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in Bar.__table__.primary_key.columns]
    assert pk_cols == ["id"]
