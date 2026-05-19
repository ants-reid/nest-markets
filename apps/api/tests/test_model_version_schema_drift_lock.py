"""Cycle 38 — Schema drift-lock for ``model_versions``.

FK target of ``signals.model_version_id``. Most important invariant
is the **anti-escalation default ``is_active=False``** — a new model
version must NEVER be auto-activated; activation must be an explicit
write. (Same guarantee already pinned for ``prompt_versions`` in
cycle 37.)

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection only.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String

from app.db.models.model_version import ModelVersion


# Ship state — column → (nullable, expected SQLAlchemy type class, optional length).
# ``temperature``/``top_p`` are declared without an explicit type class
# (SQLAlchemy infers Float); ``max_output_tokens`` is declared without an
# explicit type class (SQLAlchemy infers Integer).
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type, int | None]] = {
    "provider_name": (False, String, 100),
    "provider": (False, String, 100),
    "model_name": (False, String, 255),
    "alias_name": (True, String, 255),
    "temperature": (True, Float, None),
    "top_p": (True, Float, None),
    "max_output_tokens": (True, Integer, None),
    "reasoning_level": (True, String, 50),
    "supports_structured_output": (False, Boolean, None),
    "is_active": (False, Boolean, None),
    "notes": (True, String, 1000),
}


def test_table_name_unchanged():
    assert ModelVersion.__tablename__ == "model_versions"


def test_business_column_set_unchanged():
    table_cols = set(ModelVersion.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ModelVersion is missing column(s): {sorted(missing)}."
    assert not extra, f"ModelVersion has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ModelVersion.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ModelVersion.{col_name}.nullable changed: expected "
            f"{expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ModelVersion.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"ModelVersion.{col_name} length drifted: expected "
            f"{expected_len}, got {col.type.length}."
        )


# --------------------------------------------------------------------------- #
# Anti-escalation: is_active must default to False                            #
# --------------------------------------------------------------------------- #


def test_is_active_python_default_is_false():
    """A new model version must NEVER be auto-activated. Activation
    must be an explicit write. Same guarantee as PromptVersion."""
    col = ModelVersion.__table__.columns["is_active"]
    assert col.default is not None, (
        "ModelVersion.is_active must keep its Python default of False — "
        "anti-escalation guarantee."
    )
    assert col.default.arg is False, (
        f"ModelVersion.is_active Python default drifted: expected "
        f"False, got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )


def test_is_active_server_default_is_false():
    col = ModelVersion.__table__.columns["is_active"]
    assert col.server_default is not None, (
        "ModelVersion.is_active must keep its server_default of "
        "'false' — anti-escalation guarantee."
    )
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "false" in str(server_default_value).lower(), (
        f"ModelVersion.is_active server_default drifted: expected "
        f"'false', got {server_default_value!r}. ANTI-ESCALATION DRIFT."
    )


def test_supports_structured_output_default_true():
    """Operational default — capability flag defaults to True so a new
    provider entry is assumed compatible until proven otherwise. Locking
    this prevents silent capability flips during refactors."""
    col = ModelVersion.__table__.columns["supports_structured_output"]
    assert col.default is not None
    assert col.default.arg is True, (
        f"ModelVersion.supports_structured_output Python default drifted: "
        f"expected True, got {col.default.arg!r}."
    )


def test_id_and_created_at_supplied_by_mixins():
    cols = ModelVersion.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ModelVersion.__table__.primary_key.columns]
    assert pk_cols == ["id"]
