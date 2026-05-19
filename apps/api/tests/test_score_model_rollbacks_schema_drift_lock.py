"""Cycle 46 — Schema drift-lock for ``score_model_rollbacks``.

Audit record for every model rollback event — append-only.

Pinned shape:
  * 6 business columns + nullability + String(255) lengths
  * **BOTH FKs RESTRICT**:
      - ``from_model_id`` → score_model_registry.id RESTRICT (the
        model being rolled back FROM must remain referenceable for
        the audit trail)
      - ``to_model_id`` → score_model_registry.id RESTRICT (the model
        being rolled back TO must remain referenceable)
    Neither side can be CASCADE — a rollback row that loses both
    endpoints is an orphan that silently rewrites history.
  * ``rollback_trigger`` is non-null Enum
  * ``rollback_timestamp`` non-null timezone-aware DateTime

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String

from app.db.models.score_model_rollbacks import ScoreModelRollback


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "from_model_id": (False, None, None),  # UUID FK RESTRICT
    "to_model_id": (False, None, None),  # UUID FK RESTRICT
    "rollback_reason": (True, String, 255),
    "rollback_trigger": (False, None, None),  # Enum
    "triggered_by": (True, String, 255),
    "rollback_timestamp": (False, DateTime, None),
}


def test_table_name_unchanged():
    assert ScoreModelRollback.__tablename__ == "score_model_rollbacks"


def test_business_column_set_unchanged():
    table_cols = set(ScoreModelRollback.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ScoreModelRollback missing column(s): {sorted(missing)}."
    assert not extra, f"ScoreModelRollback has unexpected new column(s): {sorted(extra)}."


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ScoreModelRollback.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ScoreModelRollback.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ScoreModelRollback.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len


def test_both_fks_remain_restrict():
    """ANTI-DESTRUCTION: both FKs must remain RESTRICT. A rollback row
    that loses either endpoint is an orphan that silently rewrites
    history."""
    for col_name in ("from_model_id", "to_model_id"):
        col = ScoreModelRollback.__table__.columns[col_name]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert isinstance(fk, ForeignKey)
        assert fk.target_fullname == "score_model_registry.id"
        assert (fk.ondelete or "").upper() == "RESTRICT", (
            f"ScoreModelRollback.{col_name} ondelete must remain RESTRICT; "
            f"got {fk.ondelete!r}. ANTI-DESTRUCTION DRIFT."
        )


def test_rollback_timestamp_is_timezone_aware():
    col = ScoreModelRollback.__table__.columns["rollback_timestamp"]
    assert isinstance(col.type, DateTime)
    assert col.type.timezone is True


def test_id_and_timestamps_supplied_by_mixins():
    cols = ScoreModelRollback.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ScoreModelRollback.__table__.primary_key.columns]
    assert pk_cols == ["id"]
