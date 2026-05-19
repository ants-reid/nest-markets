"""Cycle 37 — Schema drift-lock for ``prompt_versions``.

``prompt_versions`` is the FK target of ``signals.prompt_version_id`` and
``llm_request_logs.prompt_version_id``. The most important invariants
this lock pins are:

  * the unique constraint ``uq_prompt_versions_role_version`` (no two
    rows can share the same (role, version) pair — without this,
    "which prompt was used" becomes ambiguous);
  * ``is_active`` default ``False`` (a new prompt version is **never**
    auto-activated; activation must be an explicit write).

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection only.
    * No imports of ``trading_control_service`` or ``BrokerService``.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Enum, String, Text, UniqueConstraint

from app.db.models.prompt_version import PromptVersion


EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "name": (False, String, 255),
    "role": (False, Enum, None),
    "version": (False, String, 50),
    "system_prompt": (False, Text, None),
    "user_template": (False, Text, None),
    "schema_json": (False, type(None), None),  # JSONB-family
    "is_active": (False, Boolean, None),
    "notes": (True, Text, None),
}


JSONB_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# --------------------------------------------------------------------------- #


def test_table_name_unchanged():
    assert PromptVersion.__tablename__ == "prompt_versions"


def test_business_column_set_unchanged():
    table_cols = set(PromptVersion.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"PromptVersion is missing column(s): {sorted(missing)}. If you "
        "intend to drop columns, ship a matrix phase + migration + "
        "ledger entry."
    )
    assert not extra, (
        f"PromptVersion has unexpected new column(s): {sorted(extra)}. "
        "If you intend to add columns, ship a matrix phase + migration "
        "+ ledger entry and update this test."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = PromptVersion.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"PromptVersion.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}. Schema drift — "
            "ship a matrix phase + migration + ledger entry."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = PromptVersion.__table__.columns[col_name]
        assert isinstance(col.type, String), (
            f"PromptVersion.{col_name} must be String (got {type(col.type).__name__})."
        )
        assert col.type.length == expected_len, (
            f"PromptVersion.{col_name} length drifted: expected "
            f"{expected_len}, got {col.type.length}."
        )


def test_schema_json_is_jsonb_family():
    col = PromptVersion.__table__.columns["schema_json"]
    type_name = type(col.type).__name__
    assert type_name in JSONB_TYPE_NAMES, (
        f"PromptVersion.schema_json must remain JSONB-family (got {type_name!r})."
    )


# --------------------------------------------------------------------------- #
# Anti-escalation: is_active must default to False                            #
# --------------------------------------------------------------------------- #


def test_is_active_python_default_is_false():
    """A new prompt version must NEVER be auto-activated. Activation
    must be an explicit write."""
    col = PromptVersion.__table__.columns["is_active"]
    assert col.default is not None, (
        "PromptVersion.is_active must keep its Python default of False — "
        "anti-escalation guarantee."
    )
    assert col.default.arg is False, (
        f"PromptVersion.is_active Python default drifted: expected "
        f"False, got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_is_active_server_default_is_false():
    """Same guarantee at the database layer."""
    col = PromptVersion.__table__.columns["is_active"]
    assert col.server_default is not None, (
        "PromptVersion.is_active must keep its server_default of "
        "'false' — anti-escalation guarantee."
    )
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "false" in str(server_default_value).lower(), (
        f"PromptVersion.is_active server_default drifted: expected "
        f"'false', got {server_default_value!r}. ANTI-ESCALATION DRIFT."
    )


# --------------------------------------------------------------------------- #
# Unique constraint                                                           #
# --------------------------------------------------------------------------- #


def test_unique_constraint_role_version_present():
    """``uq_prompt_versions_role_version`` must remain in place so two
    rows can never share the same (role, version) pair."""
    uniques = [
        c
        for c in PromptVersion.__table__.constraints
        if isinstance(c, UniqueConstraint)
    ]
    by_name = {u.name: u for u in uniques}
    assert "uq_prompt_versions_role_version" in by_name, (
        "PromptVersion is missing UniqueConstraint "
        "``uq_prompt_versions_role_version``. Without it, "
        "(role, version) pairs become non-unique and 'which prompt was "
        "used' becomes ambiguous."
    )
    cols = [c.name for c in by_name["uq_prompt_versions_role_version"].columns]
    assert cols == ["role", "version"], (
        f"UniqueConstraint columns drifted: expected ['role', 'version'], "
        f"got {cols}."
    )


def test_id_and_created_at_supplied_by_mixins():
    cols = PromptVersion.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in PromptVersion.__table__.primary_key.columns]
    assert pk_cols == ["id"], f"Primary key drifted: {pk_cols}"
