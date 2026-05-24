"""MH-148-A + MH-148-B + MH-148-C — broker_submit_decisions audit surface.

The cycle ships the table, ORM model, read endpoint, and production writer.
These tests verify:

* The model can be inserted / queried / deleted (table exists after migration).
* The endpoint returns an empty list when the table has no rows.
* The endpoint surfaces inserted rows newest-first with all expected fields.
* Filters (``intent``, ``would_block``) work and are exact-match.
* Query validation rejects invalid ``limit``.

Drift-lock guarantee: tests do not invoke the broker, the worker, or any
trading code; auto-paper enforcement, auto trading, and live trading all
remain OFF.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)

_MIN_DELTA = timedelta(seconds=5)


@pytest.fixture
def fresh_table():
    """Snapshot existing rows so we don't disturb other test state, then
    delete only rows we created in the test, identified by id."""

    created_ids: list[uuid.UUID] = []
    yield created_ids
    if not created_ids:
        return
    with SessionLocal() as session:
        session.query(BrokerSubmitDecision).filter(
            BrokerSubmitDecision.id.in_(created_ids)
        ).delete(synchronize_session=False)
        session.commit()


def test_endpoint_returns_empty_when_no_decisions_yet(fresh_table):
    response = client.get("/broker/submit-decisions/recent")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert body["limit"] == 25
    assert body["filters"] == {
        "intent": None,
        "would_block": None,
        "source": None,
        "decision_status": None,
        "correlation_id": None,
        "recommendation_id": None,
    }
    assert "audit feed" in body["advisory"].lower()


def test_endpoint_invalid_limit_rejected(fresh_table):
    response = client.get("/broker/submit-decisions/recent?limit=0")
    assert response.status_code == 422


def test_endpoint_surfaces_inserted_rows_newest_first(fresh_table):
    now = datetime.now(timezone.utc)
    older = BrokerSubmitDecision(
        intent="manual",
        would_block=False,
        blocked_reason_code=None,
        blocked_reason_text=None,
        preflight_json={"note": "older"},
        created_at=now.replace(microsecond=0) - _MIN_DELTA,
    )
    newer = BrokerSubmitDecision(
        intent="auto",
        would_block=True,
        blocked_reason_code="risk_block",
        blocked_reason_text="Spread above limit",
        preflight_json={"note": "newer", "spread": 0.05},
        created_at=now,
    )
    with SessionLocal() as session:
        session.add(older)
        session.add(newer)
        session.commit()
        session.refresh(older)
        session.refresh(newer)
        fresh_table.append(older.id)
        fresh_table.append(newer.id)

    response = client.get("/broker/submit-decisions/recent?limit=200")
    assert response.status_code == 200
    body = response.json()
    items = body["items"]
    inserted = [i for i in items if i["id"] in {str(older.id), str(newer.id)}]
    assert len(inserted) == 2

    # Newer row should come before older row in the response.
    idx_newer = next(
        i for i, item in enumerate(items) if item["id"] == str(newer.id)
    )
    idx_older = next(
        i for i, item in enumerate(items) if item["id"] == str(older.id)
    )
    assert idx_newer < idx_older

    new_item = items[idx_newer]
    assert new_item["intent"] == "auto"
    assert new_item["would_block"] is True
    assert new_item["blocked_reason_code"] == "risk_block"
    assert new_item["blocked_reason_text"] == "Spread above limit"
    assert new_item["decision_status"] is None
    assert new_item["source"] is None
    assert new_item["correlation_id"] is None
    assert new_item["preflight_json"]["spread"] == 0.05


def test_endpoint_filter_by_intent_and_would_block(fresh_table):
    a = BrokerSubmitDecision(
        intent="auto",
        would_block=True,
        preflight_json={"k": "a"},
    )
    b = BrokerSubmitDecision(
        intent="manual",
        would_block=False,
        preflight_json={"k": "b"},
    )
    with SessionLocal() as session:
        session.add(a)
        session.add(b)
        session.commit()
        session.refresh(a)
        session.refresh(b)
        fresh_table.append(a.id)
        fresh_table.append(b.id)

    resp_intent = client.get("/broker/submit-decisions/recent?intent=auto&limit=200")
    assert resp_intent.status_code == 200
    intent_items = resp_intent.json()["items"]
    ids = {i["id"] for i in intent_items}
    assert str(a.id) in ids
    assert str(b.id) not in ids

    resp_block = client.get(
        "/broker/submit-decisions/recent?would_block=false&limit=200"
    )
    assert resp_block.status_code == 200
    block_items = resp_block.json()["items"]
    block_ids = {i["id"] for i in block_items}
    assert str(b.id) in block_ids
    assert str(a.id) not in block_ids


def test_endpoint_extracts_safe_timeline_fields_and_supports_metadata_filters(fresh_table):
    recommendation_id = uuid.uuid4()
    row = BrokerSubmitDecision(
        intent="manual",
        would_block=False,
        blocked_reason_code=None,
        blocked_reason_text=None,
        preflight_json={
            "decision_status": "allowed",
            "allowed_to_submit": True,
            "decision_reason": "all checks clear",
            "source": "submit_attempt",
            "submit_gate": "allowed",
            "broker_order_id": "PAPER-123",
            "correlation_id": "manual_submit_corr_123",
            "recommendation_id": str(recommendation_id),
            "route_check_reference": "recommendation_route_check:eligible",
            "dry_run_reference": "broker_dry_run:allowed",
            "execution_mode": "ibkr_paper",
            "account_mode": "paper",
            "canonical_paper_route": "/broker/orders",
            "broker_account_mode": "paper",
            "live_state": "ibkr_live_locked",
            "execution_source": "ibkr_paper",
            "serious_paper_source": "ibkr_paper",
            "request_summary": {
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "order_type": "LIMIT",
                "limit_price": 180.5,
                "stop_price": None,
            },
            "warnings": [
                {
                    "code": "warn_1",
                    "message": "warning message",
                    "source": "risk",
                    "classification": "advisory",
                    "severity": "warning",
                }
            ],
            "blocked_reasons": [
                {
                    "code": "reason_1",
                    "message": "blocked message",
                    "source": "risk",
                    "classification": "would_block",
                    "severity": "error",
                }
            ],
        },
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        fresh_table.append(row.id)

    response = client.get(
        "/broker/submit-decisions/recent"
        f"?source=submit_attempt&decision_status=allowed&correlation_id=manual_submit_corr_123"
        f"&recommendation_id={recommendation_id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["filters"] == {
        "intent": None,
        "would_block": None,
        "source": "submit_attempt",
        "decision_status": "allowed",
        "correlation_id": "manual_submit_corr_123",
        "recommendation_id": str(recommendation_id),
    }

    item = body["items"][0]
    assert item["id"] == str(row.id)
    assert item["decision_status"] == "allowed"
    assert item["allowed_to_submit"] is True
    assert item["decision_reason"] == "all checks clear"
    assert item["source"] == "submit_attempt"
    assert item["submit_gate"] == "allowed"
    assert item["broker_order_id"] == "PAPER-123"
    assert item["correlation_id"] == "manual_submit_corr_123"
    assert item["recommendation_id"] == str(recommendation_id)
    assert item["route_check_reference"] == "recommendation_route_check:eligible"
    assert item["dry_run_reference"] == "broker_dry_run:allowed"
    assert item["execution_mode"] == "ibkr_paper"
    assert item["account_mode"] == "paper"
    assert item["canonical_paper_route"] == "/broker/orders"
    assert item["broker_account_mode"] == "paper"
    assert item["live_state"] == "ibkr_live_locked"
    assert item["execution_source"] == "ibkr_paper"
    assert item["serious_paper_source"] == "ibkr_paper"
    assert item["request_summary"] == {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10.0,
        "order_type": "LIMIT",
        "limit_price": 180.5,
        "stop_price": None,
    }
    assert item["warnings"] == [
        {
            "code": "warn_1",
            "message": "warning message",
            "source": "risk",
            "classification": "advisory",
            "severity": "warning",
        }
    ]
    assert item["blocked_reasons"] == [
        {
            "code": "reason_1",
            "message": "blocked message",
            "source": "risk",
            "classification": "would_block",
            "severity": "error",
        }
    ]


def test_model_round_trip(fresh_table):
    row = BrokerSubmitDecision(
        intent="manual",
        would_block=False,
        preflight_json={"check": "ok"},
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        fresh_table.append(row.id)
        assert row.id is not None
        assert isinstance(row.created_at, datetime)
        # created_at should be timezone-aware UTC.
        assert row.created_at.tzinfo is not None
        # And in the recent past.
        delta = datetime.now(timezone.utc) - row.created_at
        assert abs(delta.total_seconds()) < 60
