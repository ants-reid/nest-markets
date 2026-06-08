"""End-to-end API-layer tests for the full paper order flow (MH-35).

These tests exercise the complete broker order sequence using the FastAPI
TestClient — no live broker adapter required.  They are distinct from the
individual unit/route tests (MH-27 → MH-34) in that each test exercises
*multiple* API endpoints in sequence and verifies cross-step consistency.

Test map
--------
1. test_full_paper_order_chain   — health → dry-run → submit → audit (happy)
2. test_live_mode_blocks_full_chain — live guard trips dry-run AND submit
3. test_audit_sequence_order     — two dry-runs + one submit; audit preserves event order
4. test_dry_run_invalid_then_corrected — invalid dry-run followed by corrected valid one
5. test_audit_accessible_after_chain  — audit is always readable even after mixed results
6. test_health_paper_config_only_allows_dry_run — gateway down does not block dry-run
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError

from app.clients.broker.broker_interface import OrderResult
from app.config import get_settings
from app.db.models import TradingHalt
from app.db.models.broker_submit_decision import BrokerSubmitDecision
from app.db.session import SessionLocal, ensure_public_search_path
from app.main import create_app
from app.services import audit_log_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_audit_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Each test gets its own audit log file so events never bleed across tests."""
    monkeypatch.setattr(audit_log_service, "_AUDIT_LOG_PATH", tmp_path / "audit.jsonl")


@pytest.fixture(autouse=True)
def _ensure_broker_tables_and_clear_state():
    with SessionLocal() as session:
        ensure_public_search_path(session)
        try:
            session.query(TradingHalt).filter(
                TradingHalt.scope == "global",
                TradingHalt.status == "active",
            ).delete(synchronize_session=False)
            session.query(BrokerSubmitDecision).delete(synchronize_session=False)
            session.commit()
        except ProgrammingError:
            session.rollback()
    yield


def _order_payload(**overrides) -> dict:
    base = {
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "order_type": "LIMIT",
        "limit_price": 180.50,
    }
    base.update(overrides)
    return base


def _fake_submit_result(order_id: str = "PAPER-E2E-1") -> OrderResult:
    return OrderResult(
        broker_order_id=order_id,
        status="SUBMITTED",
        filled_price=Decimal("0"),
        filled_quantity=Decimal("0"),
        error_message=None,
    )


# ---------------------------------------------------------------------------
# 1. Full paper order chain: health → dry-run → submit → audit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_paper_order_chain(client: TestClient):
    """Happy-path E2E: health passes, dry-run is ready, submit succeeds, audit has both events."""
    fake_service = AsyncMock()
    fake_service.submit_order = AsyncMock(return_value=_fake_submit_result())

    # Step 1: Health check — expect paper_config_only (no live gateway in test env)
    health_resp = client.get("/broker/health")
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["mode_guard_ok"] is True
    assert health["status"] in {"paper_ready", "paper_config_only"}

    # Step 2: Dry-run — no broker service patch needed; dry_run_order is purely sync
    dry_resp = client.post("/broker/orders/dry-run", json=_order_payload())
    assert dry_resp.status_code == 200
    dry = dry_resp.json()
    assert dry["status"] == "ready"
    assert dry["mode_guard_ok"] is True
    assert dry["request_valid"] is True
    assert dry["estimated_notional"] == pytest.approx(1805.0)
    assert dry["execution_source"] == "broker_dry_run"
    assert dry["serious_paper_source"] == "ibkr_paper"
    assert dry["is_canonical_paper"] is True

    # Step 3: Submit — must succeed
    with patch("app.api.routes.broker.get_broker_service", return_value=fake_service):
        submit_resp = client.post("/broker/orders", json=_order_payload())
    assert submit_resp.status_code == 200
    result = submit_resp.json()
    assert result["status"] == "SUBMITTED"
    assert result["broker_order_id"] == "PAPER-E2E-1"

    # Step 4: Audit — must contain dry-run event then submit event
    audit_resp = client.get("/broker/orders/audit")
    assert audit_resp.status_code == 200
    entries = audit_resp.json()["entries"]
    assert len(entries) == 2

    # Audit is returned newest-first; submit comes after dry-run chronologically
    actions = [e["action"] for e in entries]
    assert "dry_run" in actions
    assert "submit" in actions

    dry_entry = next(e for e in entries if e["action"] == "dry_run")
    submit_entry = next(e for e in entries if e["action"] == "submit")

    assert dry_entry["dry_run"] is True
    assert dry_entry["ticker"] == "AAPL"
    assert dry_entry["status"] == "ready"

    assert submit_entry["dry_run"] is False
    assert submit_entry["status"] == "SUBMITTED"
    assert submit_entry["broker_order_id"] == "PAPER-E2E-1"


# ---------------------------------------------------------------------------
# 2. Live-mode guard blocks full chain (E2E negative path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_mode_blocks_full_chain(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """When LIVE_EXECUTION_ENABLED=true the guard must block both dry-run AND submit,
    and the audit trail must record BLOCKED events for both."""
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    # Step 1: Health must report misconfigured
    health_resp = client.get("/broker/health")
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["status"] == "misconfigured"
    assert health["mode_guard_ok"] is False

    # Step 2: Dry-run must return blocked (not a 4xx)
    dry_resp = client.post("/broker/orders/dry-run", json=_order_payload())
    assert dry_resp.status_code == 200
    dry = dry_resp.json()
    assert dry["status"] == "blocked"
    assert dry["mode_guard_ok"] is False
    assert any(i["code"] == "mode_guard_blocked" for i in dry["issues"])

    # Step 3: Submit must return 403
    submit_resp = client.post("/broker/orders", json=_order_payload())
    assert submit_resp.status_code == 403

    # Step 4: Audit must have both events
    audit_resp = client.get("/broker/orders/audit")
    entries = audit_resp.json()["entries"]
    assert len(entries) == 2

    dry_entry = next(e for e in entries if e["action"] == "dry_run")
    submit_entry = next(e for e in entries if e["action"] == "submit")

    assert dry_entry["status"] == "blocked"
    assert submit_entry["status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# 3. Audit sequence preserves event order for two dry-runs + one submit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_sequence_order(client: TestClient):
    """Two dry-run calls followed by one submit must appear in the audit trail in order."""
    fake_service = AsyncMock()
    fake_service.submit_order = AsyncMock(return_value=_fake_submit_result("PAPER-E2E-SEQ"))

    # Dry-runs don't need broker service patch (dry_run_order is purely sync)
    r1 = client.post("/broker/orders/dry-run", json=_order_payload())
    assert r1.json()["status"] == "ready"

    r2 = client.post("/broker/orders/dry-run", json=_order_payload())
    assert r2.json()["status"] == "ready"

    # Submit requires broker service mock
    with patch("app.api.routes.broker.get_broker_service", return_value=fake_service):
        r3 = client.post("/broker/orders", json=_order_payload())
        assert r3.json()["status"] == "SUBMITTED"

    audit_resp = client.get("/broker/orders/audit")
    entries = audit_resp.json()["entries"]
    assert len(entries) == 3

    # Audit returns newest-first; entries[0] = submit, entries[1] and [2] = dry-runs
    actions = [e["action"] for e in entries]
    assert actions[0] == "submit"
    assert actions[1] == "dry_run"
    assert actions[2] == "dry_run"


# ---------------------------------------------------------------------------
# 4. Invalid dry-run followed by corrected valid dry-run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dry_run_invalid_then_corrected(client: TestClient):
    """First dry-run with qty=0 → invalid; second with qty=10 → ready.
    Audit must record both attempts."""
    # First attempt: invalid quantity
    r1 = client.post("/broker/orders/dry-run", json=_order_payload(quantity=0))
    assert r1.status_code == 200
    assert r1.json()["status"] == "invalid"
    assert any(i["code"] == "invalid_quantity" for i in r1.json()["issues"])

    # Second attempt: corrected
    r2 = client.post("/broker/orders/dry-run", json=_order_payload(quantity=10))
    assert r2.status_code == 200
    assert r2.json()["status"] == "ready"

    audit_resp = client.get("/broker/orders/audit")
    entries = audit_resp.json()["entries"]
    assert len(entries) == 2

    statuses = [e["status"] for e in entries]
    assert "invalid" in statuses
    assert "ready" in statuses


# ---------------------------------------------------------------------------
# 5. Audit endpoint stays accessible after a mixed-result chain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_accessible_after_chain(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """Audit trail must remain readable regardless of whether operations succeeded or failed."""
    # Good dry-run
    r1 = client.post("/broker/orders/dry-run", json=_order_payload())
    assert r1.json()["status"] == "ready"

    # Bad submit attempt (live mode trips)
    monkeypatch.setenv("LIVE_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()
    r2 = client.post("/broker/orders", json=_order_payload())
    assert r2.status_code == 403

    audit_resp = client.get("/broker/orders/audit")
    assert audit_resp.status_code == 200
    entries = audit_resp.json()["entries"]
    assert len(entries) == 2

    # Both events must be present
    actions = {e["action"] for e in entries}
    assert "dry_run" in actions
    assert "submit" in actions


# ---------------------------------------------------------------------------
# 6. Gateway down (paper_config_only) still allows dry-run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_paper_config_only_allows_dry_run(client: TestClient):
    """paper_config_only health status (gateway unreachable) must not prevent dry-run.

    The dry-run only checks mode guard + request validity; it does not connect
    to the gateway.  So even when health.gateway_reachable is False, a valid
    dry-run request must return status=ready.
    """
    # Confirm health shows paper_config_only in CI (no running gateway)
    health_resp = client.get("/broker/health")
    health = health_resp.json()
    # Accept either state; the important condition is mode_guard_ok
    assert health["mode_guard_ok"] is True

    # Dry-run must still succeed regardless of gateway state
    dry_resp = client.post("/broker/orders/dry-run", json=_order_payload())
    assert dry_resp.status_code == 200
    assert dry_resp.json()["status"] == "ready"
