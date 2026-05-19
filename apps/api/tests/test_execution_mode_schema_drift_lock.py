"""Cycle 40 — Schema drift-lock for ``execution_modes``.

Locks down the available-execution-mode registry — the table that
declares which execution modes (paper / live / etc.) exist and which
of them is currently active.

Critical anti-escalation guarantees pinned here:
  * ``is_active`` defaults to ``False`` at both Python and server_default
    layers — a freshly seeded execution mode must NEVER be auto-active.
  * ``requires_approval`` defaults to ``'inactive'`` at both layers.
  * ``allows_live_orders`` defaults to ``'inactive'`` at both layers —
    a freshly seeded mode MUST NOT be permitted to send live orders.
  * ``name`` is UNIQUE so a mode name has exactly one registry row.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Enum, String

from app.db.models.execution_mode import ExecutionMode


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "name": (False, Enum, None),
    "is_active": (False, Boolean, None),
    "requires_approval": (False, String, 20),
    "allows_live_orders": (False, String, 20),
}


# (column, expected python default, expected server_default substring lower-cased)
ANTI_ESCALATION_DEFAULTS: list[tuple[str, object, str]] = [
    ("is_active", False, "false"),
    ("requires_approval", "inactive", "inactive"),
    ("allows_live_orders", "inactive", "inactive"),
]


def test_table_name_unchanged():
    assert ExecutionMode.__tablename__ == "execution_modes"


def test_business_column_set_unchanged():
    table_cols = set(ExecutionMode.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ExecutionMode is missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ExecutionMode has unexpected new column(s): {sorted(extra)}. "
        "Adding columns to a safety-config table requires an explicit "
        "phase + ledger entry."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ExecutionMode.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ExecutionMode.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ExecutionMode.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"ExecutionMode.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ExecutionMode.__table__.columns[col_name]
        assert col.type.length == expected_len, (
            f"ExecutionMode.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_name_is_unique():
    """A mode name (e.g. 'paper', 'live') must have exactly one
    registry row."""
    col = ExecutionMode.__table__.columns["name"]
    assert col.unique is True, (
        "ExecutionMode.name must be UNIQUE. Without this guard, "
        "multiple registry rows could disagree on whether a mode is "
        "active."
    )


def test_anti_escalation_defaults():
    """ANTI-ESCALATION GUARANTEE — the three safety-critical defaults
    on this table must remain at their fail-closed values:

      * is_active=False   — a new mode is INACTIVE by default
      * requires_approval='inactive'  — approval gate not bypassed
      * allows_live_orders='inactive' — live orders DENIED by default

    Flipping ANY of these silently is an anti-escalation breach.
    """
    for col_name, expected_python, expected_server_substr in ANTI_ESCALATION_DEFAULTS:
        col = ExecutionMode.__table__.columns[col_name]
        assert col.default is not None, (
            f"ExecutionMode.{col_name} lost its Python default — "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.default.arg == expected_python, (
            f"ExecutionMode.{col_name} Python default drifted: "
            f"expected {expected_python!r}, got {col.default.arg!r}. "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.server_default is not None, (
            f"ExecutionMode.{col_name} lost its server_default — "
            "ANTI-ESCALATION DRIFT."
        )
        server_default_value = col.server_default.arg
        if hasattr(server_default_value, "text"):
            server_default_value = server_default_value.text
        assert expected_server_substr in str(server_default_value).lower(), (
            f"ExecutionMode.{col_name} server_default drifted: "
            f"expected substring {expected_server_substr!r}, "
            f"got {server_default_value!r}. ANTI-ESCALATION DRIFT."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ExecutionMode.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ExecutionMode.__table__.primary_key.columns]
    assert pk_cols == ["id"]
