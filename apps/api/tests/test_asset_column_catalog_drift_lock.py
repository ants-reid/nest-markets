"""Drift-lock: Asset SQLAlchemy column catalog (cycle 72).

Pins the column names of the ``Asset`` ORM model. Renaming
``ibkr_con_id`` would silently break broker symbol resolution.

Test-only / additive.
"""

from __future__ import annotations

from app.db.models.asset import Asset

EXPECTED_COLUMNS: frozenset[str] = frozenset(
    {
        "asset_class",
        "base_currency",
        "created_at",
        "exchange",
        "ibkr_con_id",
        "id",
        "industry",
        "is_active",
        "metadata_json",
        "name",
        "quote_currency",
        "sector",
        "symbol",
        "updated_at",
    }
)

SAFETY_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {"id", "symbol", "exchange", "asset_class", "ibkr_con_id", "is_active"}
)


def _columns() -> frozenset[str]:
    return frozenset(c.name for c in Asset.__table__.columns)


def test_asset_column_catalog_exact() -> None:
    actual = _columns()
    extra = actual - EXPECTED_COLUMNS
    missing = EXPECTED_COLUMNS - actual
    msg: list[str] = []
    if extra:
        msg.append(f"  Unexpected new column(s): {sorted(extra)}")
    if missing:
        msg.append(f"  Missing expected column(s): {sorted(missing)}")
    assert not msg, (
        "Asset column catalog drift detected.\n"
        + "\n".join(msg)
        + "\nIf intentional, ALSO add an alembic migration."
    )


def test_asset_safety_columns_present() -> None:
    actual = _columns()
    missing = SAFETY_REQUIRED_COLUMNS - actual
    assert not missing, (
        f"Asset missing safety/resolution column(s): {sorted(missing)}."
    )
