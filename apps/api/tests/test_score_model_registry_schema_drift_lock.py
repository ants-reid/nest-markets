"""Cycle 46 — Schema drift-lock for ``score_model_registry``.

Locks the trained-model registry table — root of the score-model
lifecycle quintet. Every promotion / rollback / evaluation /
parameter row FKs back here.

Pinned shape:
  * 11 business columns + nullability + String lengths
  * UNIQUE (strategy_bucket, asset_class, version_number) named
    ``uq_smr_bucket_asset_version`` — prevents two competing
    registry rows for the same bucket/asset/version
  * Indexes: ``ix_smr_status``, ``ix_smr_is_active``
  * **ANTI-ESCALATION** ``status`` defaults to ``'candidate'``
    (CANDIDATE enum) — a fresh row must NEVER default to ``'active'``
    (would silently promote an untrained model)
  * **ANTI-ESCALATION** ``is_active`` defaults to ``False`` at BOTH
    Python and server_default layers (a flip to True would silently
    activate every newly-registered model)

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, String, Text

from app.db.models.score_model_registry import ScoreModelRegistry


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "name": (False, String, 255),
    "version_number": (False, Integer, None),
    "strategy_bucket": (False, String, 100),
    "asset_class": (False, String, 50),
    "description": (True, Text, None),
    "training_date": (False, DateTime, None),
    "trained_by": (True, String, 255),
    "status": (False, None, None),  # Enum
    "is_active": (False, Boolean, None),
    "promoted_at": (True, DateTime, None),
    "promoted_by": (True, String, 255),
}


def test_table_name_unchanged():
    assert ScoreModelRegistry.__tablename__ == "score_model_registry"


def test_business_column_set_unchanged():
    table_cols = set(ScoreModelRegistry.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at", "updated_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ScoreModelRegistry missing column(s): {sorted(missing)}."
    assert not extra, f"ScoreModelRegistry has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ScoreModelRegistry.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ScoreModelRegistry.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ScoreModelRegistry.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"ScoreModelRegistry.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_uq_bucket_asset_version_present():
    constraint_names = {c.name for c in ScoreModelRegistry.__table__.constraints if c.name}
    assert "uq_smr_bucket_asset_version" in constraint_names, (
        "UNIQUE (strategy_bucket, asset_class, version_number) constraint missing."
    )


def test_expected_indexes_present():
    indexes_by_name = {idx.name: idx for idx in ScoreModelRegistry.__table__.indexes}
    for name in ("ix_smr_status", "ix_smr_is_active"):
        assert name in indexes_by_name, f"Index {name} is missing."


def test_status_anti_escalation_default_candidate():
    """ANTI-ESCALATION: status defaults to 'candidate'. A flip to
    'active' would silently promote every newly-registered (untrained)
    model into production scoring."""
    col = ScoreModelRegistry.__table__.columns["status"]
    assert col.nullable is False
    assert col.default is not None, (
        "ScoreModelRegistry.status lost its Python default — ANTI-ESCALATION DRIFT."
    )
    default_value = col.default.arg
    default_str = getattr(default_value, "value", default_value)
    assert default_str == "candidate", (
        f"ScoreModelRegistry.status default drifted: expected 'candidate', "
        f"got {default_value!r} (resolved={default_str!r}). ANTI-ESCALATION DRIFT."
    )


def test_is_active_default_false_both_layers():
    """ANTI-ESCALATION: is_active=False at BOTH Python and server_default
    layers. A flip to True would silently activate every newly-registered
    model regardless of validation."""
    col = ScoreModelRegistry.__table__.columns["is_active"]
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg is False, (
        f"ScoreModelRegistry.is_active Python default drifted: "
        f"expected False, got {col.default.arg!r}. ANTI-ESCALATION DRIFT."
    )
    assert col.server_default is not None, (
        "ScoreModelRegistry.is_active lost its server_default — ANTI-ESCALATION DRIFT."
    )
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "false" in str(server_default_value).lower(), (
        f"ScoreModelRegistry.is_active server_default drifted: "
        f"got {server_default_value!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ScoreModelRegistry.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    pk_cols = [c.name for c in ScoreModelRegistry.__table__.primary_key.columns]
    assert pk_cols == ["id"]
