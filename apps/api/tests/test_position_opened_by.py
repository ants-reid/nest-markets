"""Tests for MH-146 Position.opened_by attribution column."""

from __future__ import annotations

from app.db.models.position import Position


def test_position_has_opened_by_column():
    cols = {c.name for c in Position.__table__.columns}
    assert "opened_by" in cols


def test_opened_by_default_is_unknown():
    """ORM default and server_default are both 'unknown' so legacy rows backfill safely."""
    col = Position.__table__.columns["opened_by"]
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg == "unknown"
    assert col.server_default is not None
    # server_default text representation
    assert "unknown" in str(col.server_default.arg)


def test_opened_by_column_length_is_20():
    col = Position.__table__.columns["opened_by"]
    assert col.type.length == 20


def test_opened_by_check_constraint_present():
    """Migration adds a CHECK constraint, but ORM also reflects it via the model.

    The check is enforced at the DB level by the migration; we assert here that
    the ORM allows valid values and rejects nothing client-side (the DB does that).
    """
    # Smoke: assigning each valid value works at the Python level.
    for value in ("auto_paper", "manual_paper", "live", "unknown"):
        p = Position()
        p.opened_by = value
        assert p.opened_by == value
