"""Cycle 40 — Schema drift-lock for ``execution_policies``.

Locks the per-(asset_class, mode) execution policy table that gates
which sides (long/short), timeframes, and confirmation/paper-only
behaviour are allowed for a given combination.

Critical anti-escalation guarantees pinned here:
  * ``paper_only`` defaults to ``True`` at both Python and server_default
    layers — a freshly seeded policy MUST be paper-only by default;
    flipping this silently would let real orders go to a live broker.
  * ``requires_user_confirmation`` defaults to ``False`` at both layers
    (this is the *expected* shipped baseline; it is pinned so the
    field cannot silently change semantics without explicit ledger
    notice).
  * ``allow_long`` / ``allow_short`` default ``True`` — pinned so a
    refactor cannot silently widen or narrow the trading sides.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Enum

from app.db.models.execution_policy import ExecutionPolicy


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None]] = {
    "asset_class": (False, Enum),
    "mode": (False, Enum),
    "allow_long": (False, Boolean),
    "allow_short": (False, Boolean),
    "allowed_timeframes_json": (True, None),  # JSONB-family; checked separately
    "requires_user_confirmation": (False, Boolean),
    "paper_only": (False, Boolean),
}


# (column, expected python default, expected server_default substring lower-cased)
ANTI_ESCALATION_DEFAULTS: list[tuple[str, object, str]] = [
    ("paper_only", True, "true"),
    ("requires_user_confirmation", False, "false"),
    ("allow_long", True, "true"),
    ("allow_short", True, "true"),
]


def test_table_name_unchanged():
    assert ExecutionPolicy.__tablename__ == "execution_policies"


def test_business_column_set_unchanged():
    table_cols = set(ExecutionPolicy.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ExecutionPolicy missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ExecutionPolicy has unexpected new column(s): {sorted(extra)}. "
        "Adding columns to a safety-config table requires an explicit "
        "phase + ledger entry."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ExecutionPolicy.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ExecutionPolicy.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = ExecutionPolicy.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"ExecutionPolicy.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_allowed_timeframes_is_jsonb_family():
    col = ExecutionPolicy.__table__.columns["allowed_timeframes_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES, (
        f"ExecutionPolicy.allowed_timeframes_json must remain a "
        f"JSONB-family column; got {type_name}."
    )


def test_anti_escalation_defaults():
    """ANTI-ESCALATION GUARANTEE — paper_only must default True;
    requires_user_confirmation must default False (pinned baseline);
    allow_long / allow_short must default True (pinned baseline).
    Any silent flip is a drift-lock breach.
    """
    for col_name, expected_python, expected_server_substr in ANTI_ESCALATION_DEFAULTS:
        col = ExecutionPolicy.__table__.columns[col_name]
        assert col.default is not None, (
            f"ExecutionPolicy.{col_name} lost its Python default — "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.default.arg is expected_python, (
            f"ExecutionPolicy.{col_name} Python default drifted: "
            f"expected {expected_python!r}, got {col.default.arg!r}. "
            "ANTI-ESCALATION DRIFT."
        )
        assert col.server_default is not None, (
            f"ExecutionPolicy.{col_name} lost its server_default — "
            "ANTI-ESCALATION DRIFT."
        )
        server_default_value = col.server_default.arg
        if hasattr(server_default_value, "text"):
            server_default_value = server_default_value.text
        assert expected_server_substr in str(server_default_value).lower(), (
            f"ExecutionPolicy.{col_name} server_default drifted: "
            f"expected substring {expected_server_substr!r}, "
            f"got {server_default_value!r}. ANTI-ESCALATION DRIFT."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ExecutionPolicy.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ExecutionPolicy.__table__.primary_key.columns]
    assert pk_cols == ["id"]
