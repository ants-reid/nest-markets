"""Cycle 42 — Schema drift-lock for ``approval_requests``.

Locks the user-approval-request table for confirm-before-trade mode.
This is the dependency surface of MH-COCKPIT-14 (Assisted Live Trade
mode UI — Bucket 4 LOCKED) and MH-NEWS-05L (News Risk gate for live).

Pinned shape:
  * 12 business columns, full nullability map
  * String lengths (status=50, responded_by/approved_by/rejected_by=255,
    notes=1000)
  * FK signal_id -> signals.id (nullable)
  * **ANTI-ESCALATION**: ``status`` defaults to ``'pending'`` at the
    Python layer. A fresh approval-request row must NEVER default to
    'approved' — that would let a write be silently auto-approved
    bypassing the confirm-before-trade gate.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Read-only ORM-introspection.
"""

from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String

from app.db.models.approval_request import ApprovalRequest


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "signal_id": (True, None, None),  # UUID FK
    "risk_decision_id": (True, None, None),  # UUID
    "status": (False, String, 50),
    "timestamp": (True, DateTime, None),
    "requested_at": (True, DateTime, None),
    "responded_at": (True, DateTime, None),
    "responded_by": (True, String, 255),
    "approved_by": (True, String, 255),
    "approved_at": (True, DateTime, None),
    "rejected_by": (True, String, 255),
    "expired_at": (True, DateTime, None),
    "notes": (True, String, 1000),
    "expires_at": (True, DateTime, None),
}


EXPECTED_FOREIGN_KEYS: dict[str, str] = {
    "signal_id": "signals.id",
}


def test_table_name_unchanged():
    assert ApprovalRequest.__tablename__ == "approval_requests"


def test_business_column_set_unchanged():
    table_cols = set(ApprovalRequest.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, f"ApprovalRequest missing column(s): {sorted(missing)}."
    assert not extra, (
        f"ApprovalRequest has unexpected new column(s): {sorted(extra)}. "
        "Adding columns to the approval-gate table requires an explicit "
        "phase + ledger entry — Bucket-4 dependency surface."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ApprovalRequest.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ApprovalRequest.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ApprovalRequest.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"ApprovalRequest.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_expected_foreign_keys_present():
    for col_name, expected_target in EXPECTED_FOREIGN_KEYS.items():
        col = ApprovalRequest.__table__.columns[col_name]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert expected_target in fk_targets, (
            f"ApprovalRequest.{col_name} must keep FK -> "
            f"{expected_target}; got {fk_targets}."
        )
        assert any(isinstance(fk, ForeignKey) for fk in col.foreign_keys)


def test_status_anti_escalation_default():
    """ANTI-ESCALATION GUARANTEE: a fresh approval row must default to
    ``status='pending'``. A silent flip to 'approved' would let a
    write be auto-approved bypassing the confirm-before-trade gate.
    """
    col = ApprovalRequest.__table__.columns["status"]
    assert col.nullable is False, (
        "ApprovalRequest.status must remain NOT NULL — ANTI-ESCALATION."
    )
    assert col.default is not None, (
        "ApprovalRequest.status lost its Python default — "
        "ANTI-ESCALATION DRIFT."
    )
    assert col.default.arg == "pending", (
        f"ApprovalRequest.status Python default drifted: expected "
        f"'pending', got {col.default.arg!r}. ANTI-ESCALATION DRIFT — "
        "a fresh approval row must NEVER default to 'approved'."
    )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ApprovalRequest.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ApprovalRequest.__table__.primary_key.columns]
    assert pk_cols == ["id"]
