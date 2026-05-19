"""MH-RISK-AUDIT-A — Tests for ``GET /risk-decisions/recent`` endpoint.

These tests seed rows directly via the ORM (the production writer is
``risk_service.py`` / ``persistence_signal_service.py``; we do not invoke
those here to keep the test surface narrow and additive).

We deliberately leave ``signal_id`` as NULL on seed rows because the
column has an FK to ``signals.id`` and creating real signals would
expand the surface beyond the cycle's scope. Seeded rows are
discriminated from any pre-existing data via unique
``block_reason_code`` markers and the cleanup fixture below.

Drift-lock guarantee: tests do not invoke the worker, the broker, the
risk evaluator, or any trading code.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.models.risk_decision import RiskDecision
from app.db.session import SessionLocal
from app.main import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


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


def _seed(rows: list[RiskDecision]) -> None:
    with SessionLocal() as session:
        for row in rows:
            session.add(row)
        session.commit()
        for row in rows:
            session.refresh(row)


def _unique_marker() -> str:
    # Stays within the 64-char column limit and is unique per test.
    return f"TEST_{uuid.uuid4().hex[:24]}"


def test_endpoint_returns_envelope_and_advisory(client):
    resp = client.get("/risk-decisions/recent?limit=1")
    assert resp.status_code == 200
    body = resp.json()
    assert "advisory" in body and "Drift-lock" in body["advisory"]
    assert "items" in body
    assert "count" in body and body["count"] == len(body["items"])
    assert body["limit"] == 1
    assert body["filters"] == {
        "approved": None,
        "signal_id": None,
        "block_reason_code": None,
    }


def test_invalid_limit_returns_422(client):
    resp = client.get("/risk-decisions/recent?limit=0")
    assert resp.status_code == 422
    resp2 = client.get("/risk-decisions/recent?limit=999")
    assert resp2.status_code == 422


def test_newest_first_ordering_via_marker_filter(client, created_ids):
    marker = _unique_marker()
    base = datetime.now(timezone.utc)
    rows = [
        RiskDecision(
            approved="blocked",
            blocking_rule="ordering_test",
            block_reason_code=marker,
            created_at=base - timedelta(minutes=10 - i),
        )
        for i in range(3)
    ]
    _seed(rows)
    created_ids.extend([r.id for r in rows])

    resp = client.get(
        f"/risk-decisions/recent?block_reason_code={marker}&limit=10"
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 3
    assert {it["block_reason_code"] for it in items} == {marker}
    # Newest-first ordering by created_at.
    assert items[0]["created_at"] > items[1]["created_at"] > items[2]["created_at"]


def test_approved_filter_combines_with_marker(client, created_ids):
    marker = _unique_marker()
    base = datetime.now(timezone.utc)
    a = RiskDecision(
        approved="blocked",
        blocking_rule="spread_exceeded",
        block_reason_code=marker,
        created_at=base,
    )
    b = RiskDecision(
        approved="approved",
        blocking_rule=None,
        block_reason_code=marker,
        created_at=base + timedelta(seconds=1),
    )
    c = RiskDecision(
        approved="blocked",
        blocking_rule="cooldown",
        block_reason_code=marker,
        created_at=base + timedelta(seconds=2),
    )
    _seed([a, b, c])
    created_ids.extend([a.id, b.id, c.id])

    r1 = client.get(
        f"/risk-decisions/recent?block_reason_code={marker}&approved=blocked&limit=50"
    )
    assert r1.status_code == 200
    items = r1.json()["items"]
    assert len(items) == 2
    assert {it["blocking_rule"] for it in items} == {
        "spread_exceeded",
        "cooldown",
    }

    r2 = client.get(
        f"/risk-decisions/recent?block_reason_code={marker}&limit=50"
    )
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 3


def test_serialization_shape_includes_safety_attribution_columns(
    client, created_ids
):
    marker = _unique_marker()
    profile_id = uuid.uuid4()
    row = RiskDecision(
        approved="approved",
        risk_profile_id=profile_id,
        block_reason_code=marker,
        created_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    _seed([row])
    created_ids.append(row.id)

    resp = client.get(
        f"/risk-decisions/recent?block_reason_code={marker}&limit=10"
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    found = items[0]
    for key in (
        "id",
        "created_at",
        "signal_id",
        "approved",
        "blocking_rule",
        "block_reason_code",
        "risk_profile_id",
    ):
        assert key in found, f"missing key: {key}"
    assert found["risk_profile_id"] == str(profile_id)
    assert found["signal_id"] is None
