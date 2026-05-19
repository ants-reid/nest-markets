"""MH-MON-04-MATRIX-VERIFY — Trading-safety aggregator invariance test.

Asserts that touching every read-only audit / monitor / worker-run-log
endpoint shipped through cycle 28 does NOT change the verdict returned
by ``evaluate_trading_safety()``. Specifically the critical drift-lock
fields (``auto_trading_allowed``, ``trading_mode``, ``execution_control``,
``arming_state``, ``halt_active``) must be identical before AND after the
audit traversal.

This is a read-only behavioural snapshot test. It does not modify any
production code.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.trading_safety_aggregator import evaluate_trading_safety


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


READ_ONLY_TRAVERSAL_PATHS = [
    # cycles 23-28 audit endpoints
    "/broker/submit-decisions/recent?limit=1",
    "/news-in-decision-log/recent?limit=1",
    "/risk-decisions/recent?limit=1",
    "/llm-logs/recent?limit=1",
    # monitor surfaces
    "/monitor/worker-run-log/overview?limit=1",
]


def _verdict_snapshot() -> dict:
    """Capture the drift-lock-critical subset of evaluate_trading_safety()."""
    decision = evaluate_trading_safety()
    payload = decision.to_dict()
    return {
        "auto_trading_allowed": payload["auto_trading_allowed"],
        "trading_mode": payload["trading_mode"],
        "execution_control": payload["execution_control"],
        "arming_state": payload["arming_state"],
        "halt_active": payload["halt_active"],
    }


def test_safety_aggregator_verdict_is_invariant_across_audit_reads(client):
    """The audit traversal must not change the safety verdict at all."""
    before = _verdict_snapshot()
    # Sanity: drift lock must already be ON.
    assert before["auto_trading_allowed"] is False, (
        "Pre-condition violated: auto_trading_allowed is True; "
        "drift lock is already broken."
    )

    for path in READ_ONLY_TRAVERSAL_PATHS:
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"endpoint {path} returned {resp.status_code}: "
            f"{resp.text[:200]}"
        )

    after = _verdict_snapshot()
    assert after == before, (
        "Trading-safety verdict CHANGED across read-only audit traversal. "
        f"before={before} after={after} — drift-lock regression."
    )
    assert after["auto_trading_allowed"] is False, (
        "auto_trading_allowed flipped to True after audit traversal — "
        "drift lock broken."
    )
