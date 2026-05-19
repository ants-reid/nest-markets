"""Cycle 41 — Schema drift-lock for ``paper_orders``.

Locks the simulated-order record table — the durable receipt of every
order the auto-paper worker would submit. With auto-paper enforcement
OFF (per drift-lock), this table is read-by-tests but currently
write-quiet; pinning its shape now means any future writer landing in
MH-145-B / MH-148-C / MH-152 must ship additively.

Pinned shape:
  * 19 business columns, full nullability map
  * String lengths (order_type/status/ibkr_status=50, side/direction=20)
  * Numeric precision (18,8) for all price/qty/notional/commission cols
  * FK signal_id -> signals.id (nullable)
  * status default 'pending' (Python layer only — server_default not
    declared; pinned so a refactor can't silently change it)
  * filled_quantity default 0.0 at both layers

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Numeric, String

from app.db.models.paper_order import PaperOrder


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "signal_id": (True, None, None),  # UUID FK
    "asset_id": (True, None, None),  # UUID
    "risk_decision_id": (True, None, None),  # UUID
    "order_type": (True, String, 50),
    "side": (True, String, 20),
    "direction": (True, String, 20),
    "qty": (True, Numeric, None),
    "quantity": (True, Numeric, None),
    "filled_quantity": (False, Numeric, None),
    "notional": (True, Numeric, None),
    "limit_price": (True, Numeric, None),
    "stop_price": (True, Numeric, None),
    "status": (False, String, 50),
    "timestamp": (True, DateTime, None),
    "submitted_at": (True, DateTime, None),
    "broker_order_id": (True, None, None),
    "commission": (True, Numeric, None),
    "avg_fill_price": (True, Numeric, None),
    "ibkr_status": (True, String, 50),
}


# All Numeric columns must remain (18, 8) — currency/qty semantics
PINNED_NUMERIC_18_8: list[str] = [
    "qty",
    "quantity",
    "filled_quantity",
    "notional",
    "limit_price",
    "stop_price",
    "commission",
    "avg_fill_price",
]


# Expected FK targets (column -> referenced "table.column")
EXPECTED_FOREIGN_KEYS: dict[str, str] = {
    "signal_id": "signals.id",
}


def test_table_name_unchanged():
    assert PaperOrder.__tablename__ == "paper_orders"


def test_business_column_set_unchanged():
    table_cols = set(PaperOrder.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"PaperOrder is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"PaperOrder has unexpected new column(s): {sorted(extra)}. "
        "Adding columns to an order-result table requires an explicit "
        "phase + ledger entry."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PaperOrder.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PaperOrder.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = PaperOrder.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"PaperOrder.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_numeric_precision_unchanged():
    for col_name in PINNED_NUMERIC_18_8:
        col = PaperOrder.__table__.columns[col_name]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 18, (
            f"PaperOrder.{col_name} precision drifted: expected 18, "
            f"got {col.type.precision}."
        )
        assert col.type.scale == 8, (
            f"PaperOrder.{col_name} scale drifted: expected 8, "
            f"got {col.type.scale}."
        )


def test_expected_foreign_keys_present():
    for col_name, expected_target in EXPECTED_FOREIGN_KEYS.items():
        col = PaperOrder.__table__.columns[col_name]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert expected_target in fk_targets, (
            f"PaperOrder.{col_name} must keep FK -> {expected_target}; "
            f"got {fk_targets}."
        )
        # Must be a real ForeignKey object, not a bare UUID column.
        assert any(isinstance(fk, ForeignKey) for fk in col.foreign_keys)


def test_status_default_is_pending():
    """``status`` defaults to 'pending' at the Python layer. A new
    PaperOrder row must NEVER default to a terminal/final state like
    'filled' or 'submitted' — the worker must explicitly transition it.
    """
    col = PaperOrder.__table__.columns["status"]
    assert col.default is not None, (
        "PaperOrder.status lost its Python default — a row could now "
        "be created without an explicit status, which masks state-"
        "machine drift."
    )
    assert col.default.arg == "pending", (
        f"PaperOrder.status Python default drifted: expected 'pending', "
        f"got {col.default.arg!r}. State-machine drift breach."
    )


def test_filled_quantity_default_is_zero():
    """``filled_quantity`` defaults to 0.0 at both layers. Any
    drift here would mean a fresh order row could appear partially
    filled before the broker reports anything.
    """
    col = PaperOrder.__table__.columns["filled_quantity"]
    assert col.default is not None
    assert col.default.arg == 0.0
    assert col.server_default is not None
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "0" in str(server_default_value), (
        f"PaperOrder.filled_quantity server_default drifted: "
        f"got {server_default_value!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = PaperOrder.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in PaperOrder.__table__.primary_key.columns]
    assert pk_cols == ["id"]
