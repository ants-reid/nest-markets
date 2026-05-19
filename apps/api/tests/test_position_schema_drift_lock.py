"""Cycle 35 — Schema drift-lock for ``positions`` (mirror of cycle 33/34).

Locks down the ``positions`` table including the MH-146
``opened_by`` column (VARCHAR(20), NOT NULL, default ``'unknown'``,
CHECK ``opened_by IN ('auto_paper','manual_paper','live','unknown')``,
index ``ix_positions_opened_by_status``).

Uses ORM-introspection for column shape and a raw-DB ``information_schema``
read for the CHECK constraint and the index (those are not surfaced on
the SQLAlchemy ``Table`` object directly when added via
``op.create_check_constraint`` / ``op.create_index`` in a migration).

Drift-lock notes:
    * Pure additive test; no production code change.
    * No imports of ``trading_control_service`` or ``BrokerService``.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Enum, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.position import Position
from app.db.session import SessionLocal


# Ship state — column name → (nullable, expected SQLAlchemy type class).
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type]] = {
    "asset_id": (False, UUID),
    "signal_id": (True, UUID),
    "status": (False, Enum),
    "side": (False, String),
    "avg_entry_price": (True, Numeric),
    "current_price": (True, Numeric),
    "stop_price": (True, Numeric),
    "target_price": (True, Numeric),
    "qty": (True, Numeric),
    "opened_at": (True, DateTime),
    "closed_at": (True, DateTime),
    "close_reason": (True, String),
    "realized_pnl": (True, Numeric),
    "unrealized_pnl": (True, Numeric),
    "max_favorable_excursion": (True, Numeric),
    "max_adverse_excursion": (True, Numeric),
    "broker_order_id": (True, String),
    "ibkr_con_id": (True, type(None)),  # plain Integer (no explicit class)
    "market_value": (True, Numeric),
    "commission_paid": (True, Numeric),
    "close_price": (True, Numeric),
    "opened_by": (False, String),  # MH-146
}


EXPECTED_OPENED_BY_VALUES: frozenset[str] = frozenset(
    {"auto_paper", "manual_paper", "live", "unknown"}
)


# --------------------------------------------------------------------------- #
# Table-level invariants                                                      #
# --------------------------------------------------------------------------- #


def test_table_name_unchanged():
    assert Position.__tablename__ == "positions"


def test_business_column_set_unchanged():
    """The business-column set (excluding mixin-supplied bookkeeping
    columns) must match the current ship state exactly."""
    table_cols = set(Position.__table__.columns.keys())
    # TimestampMixin contributes ``created_at`` and ``updated_at``.
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"Position is missing column(s): {sorted(missing)}. If you "
        "intend to drop columns, ship a matrix phase + migration + "
        "ledger entry."
    )
    assert not extra, (
        f"Position has unexpected new column(s): {sorted(extra)}. If "
        "you intend to add columns, ship a matrix phase + migration + "
        "ledger entry and update this test."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _expected_type) in EXPECTED_BUSINESS_COLUMNS.items():
        col = Position.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"Position.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}. Schema drift — "
            "ship a matrix phase + migration + ledger entry."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = Position.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in Position.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"


# --------------------------------------------------------------------------- #
# MH-146 ``opened_by`` invariants                                             #
# --------------------------------------------------------------------------- #


def test_opened_by_column_shape():
    """``opened_by`` must remain VARCHAR(20), NOT NULL, with both Python
    default ``'unknown'`` and server_default ``'unknown'``."""
    col = Position.__table__.columns["opened_by"]
    assert isinstance(col.type, String), (
        f"Position.opened_by must be a String type (got {type(col.type).__name__})."
    )
    assert col.type.length == 20, (
        f"Position.opened_by length drifted: expected 20, got {col.type.length}."
    )
    assert col.nullable is False, "Position.opened_by must remain NOT NULL."
    # Python-side default
    assert col.default is not None, "Position.opened_by must keep its Python default."
    assert col.default.arg == "unknown", (
        f"Position.opened_by Python default drifted: expected 'unknown', "
        f"got {col.default.arg!r}."
    )
    # Server-side default
    assert col.server_default is not None, (
        "Position.opened_by must keep its server_default for safe legacy backfill."
    )
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "unknown" in str(server_default_value), (
        f"Position.opened_by server_default drifted: expected 'unknown', "
        f"got {server_default_value!r}."
    )


def test_opened_by_check_constraint_present_in_db():
    """The MH-146 CHECK constraint ``ck_positions_opened_by`` must
    exist in the live DB and reference all four allowed values."""
    with SessionLocal() as session:
        row = session.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid) AS def
                FROM pg_constraint
                WHERE conname = 'ck_positions_opened_by'
                  AND conrelid = 'positions'::regclass
                """
            )
        ).first()
    assert row is not None, (
        "MH-146 CHECK constraint ``ck_positions_opened_by`` is missing "
        "from the live DB. Run ``alembic upgrade head`` and verify the "
        "MH-146 migration is applied."
    )
    constraint_def = row.def_ if hasattr(row, "def_") else row[0]
    for expected_value in EXPECTED_OPENED_BY_VALUES:
        assert expected_value in constraint_def, (
            f"CHECK ck_positions_opened_by no longer references "
            f"``{expected_value}``. Constraint def: {constraint_def!r}."
        )


def test_opened_by_index_present_in_db():
    """The MH-146 index ``ix_positions_opened_by_status`` must exist
    and cover ``(opened_by, status)`` for the auto-paper cap query."""
    with SessionLocal() as session:
        row = session.execute(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'positions'
                  AND indexname = 'ix_positions_opened_by_status'
                """
            )
        ).first()
    assert row is not None, (
        "MH-146 index ``ix_positions_opened_by_status`` is missing "
        "from the live DB. Run ``alembic upgrade head``."
    )
    indexdef = row.indexdef if hasattr(row, "indexdef") else row[0]
    assert "opened_by" in indexdef and "status" in indexdef, (
        f"Index ix_positions_opened_by_status drifted; expected "
        f"(opened_by, status). Got: {indexdef!r}."
    )
