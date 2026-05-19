"""MH-153-A + MH-154-A — additive nullable columns on ``risk_decisions``.

Verifies the new columns exist on the model and accept None / a value, and
that no existing column was disturbed. No production writer is wired in
this cycle, so these tests act as a structural smoke-check only.

Drift-lock guarantee: tests do not invoke the worker, the broker, the risk
service, or any trading code; auto-paper enforcement, auto trading, and
live trading all remain OFF.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect

from app.db.models.risk_decision import RiskDecision
from app.db.session import SessionLocal


@pytest.fixture
def created_ids():
    ids: list[uuid.UUID] = []
    yield ids
    if not ids:
        return
    with SessionLocal() as session:
        session.query(RiskDecision).filter(
            RiskDecision.id.in_(ids)
        ).delete(synchronize_session=False)
        session.commit()


def test_model_has_new_additive_columns():
    cols = {c.name for c in inspect(RiskDecision).columns}
    assert "risk_profile_id" in cols  # MH-153-A
    assert "block_reason_code" in cols  # MH-154-A
    # Pre-existing columns must still be present.
    for legacy in (
        "blocking_rule",
        "blocked_reasons_json",
        "spread_ok",
        "drawdown_ok",
        "decision_json",
    ):
        assert legacy in cols


def test_new_columns_default_to_none(created_ids):
    row = RiskDecision(approved="pending")
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        created_ids.append(row.id)
        assert row.risk_profile_id is None
        assert row.block_reason_code is None


def test_new_columns_accept_values_and_round_trip(created_ids):
    profile_id = uuid.uuid4()
    row = RiskDecision(
        approved="rejected",
        risk_profile_id=profile_id,
        block_reason_code="SPREAD_TOO_WIDE",
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        created_ids.append(row.id)

    with SessionLocal() as session:
        fetched = session.get(RiskDecision, row.id)
        assert fetched is not None
        assert fetched.risk_profile_id == profile_id
        assert fetched.block_reason_code == "SPREAD_TOO_WIDE"
        # Pre-existing columns still default to None when not set.
        assert fetched.blocking_rule is None
        assert fetched.blocked_reasons_json is None
