"""Cycle 46 — Schema drift-lock for ``score_model_promotions``.

Audit record for every model promotion event — append-only.

Pinned shape:
  * 7 business columns + nullability
  * **FK ondelete asymmetry**:
      - ``from_model_id`` → score_model_registry.id ondelete=SET NULL
        (an old model can be archived without erasing the audit trail)
      - ``to_model_id`` → score_model_registry.id ondelete=RESTRICT
        (you must NEVER be able to delete a model that is the target
        of a promotion record — would orphan production scoring)
  * ``promotion_type`` is non-null Enum
  * ``promoted_at`` non-null timezone-aware DateTime
  * **ANTI-ESCALATION-INVERSE** ``rollback_eligible`` defaults to
    ``True`` at BOTH Python and server_default layers — a flip to
    False would silently strip rollback eligibility from every new
    promotion (operators would be unable to revert a bad promo)

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Text

from app.db.models.score_model_promotions import ScoreModelPromotion


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "from_model_id": (True, None, None),  # UUID FK SET NULL
    "to_model_id": (False, None, None),  # UUID FK RESTRICT
    "promotion_type": (False, None, None),  # Enum
    "promoted_at": (False, DateTime, None),
    "promoted_by": (True, None, None),  # no explicit type
    "approval_notes": (True, Text, None),
    "rollback_eligible": (False, Boolean, None),
}


def test_table_name_unchanged():
    assert ScoreModelPromotion.__tablename__ == "score_model_promotions"


def test_business_column_set_unchanged():
    table_cols = set(ScoreModelPromotion.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ScoreModelPromotion missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ScoreModelPromotion has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ScoreModelPromotion.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ScoreModelPromotion.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_from_model_fk_set_null():
    """from_model_id FK must remain SET NULL — an old model can be
    archived without erasing the audit trail."""
    col = ScoreModelPromotion.__table__.columns["from_model_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "score_model_registry.id"
    assert (fk.ondelete or "").upper() == "SET NULL", (
        f"from_model_id ondelete must remain SET NULL; got {fk.ondelete!r}."
    )


def test_to_model_fk_restrict():
    """ANTI-DESTRUCTION: to_model_id FK must remain RESTRICT —
    deleting a model that is the target of a promotion would orphan
    production scoring."""
    col = ScoreModelPromotion.__table__.columns["to_model_id"]
    fks = list(col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert isinstance(fk, ForeignKey)
    assert fk.target_fullname == "score_model_registry.id"
    assert (fk.ondelete or "").upper() == "RESTRICT", (
        f"to_model_id ondelete must remain RESTRICT; got {fk.ondelete!r}. "
        "ANTI-DESTRUCTION DRIFT."
    )


def test_promoted_at_is_timezone_aware():
    col = ScoreModelPromotion.__table__.columns["promoted_at"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True


def test_rollback_eligible_default_true_both_layers():
    """ANTI-ESCALATION-INVERSE: rollback_eligible=True at BOTH Python
    and server_default layers. A flip to False would silently strip
    rollback eligibility from every new promotion."""
    col = ScoreModelPromotion.__table__.columns["rollback_eligible"]
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg is True, (
        f"ScoreModelPromotion.rollback_eligible Python default drifted: "
        f"expected True, got {col.default.arg!r}."
    )
    assert col.server_default is not None
    server_default_value = col.server_default.arg
    if hasattr(server_default_value, "text"):
        server_default_value = server_default_value.text
    assert "true" in str(server_default_value).lower(), (
        f"ScoreModelPromotion.rollback_eligible server_default drifted: "
        f"got {server_default_value!r}."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ScoreModelPromotion.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ScoreModelPromotion.__table__.primary_key.columns]
    assert pk_cols == ["id"]
