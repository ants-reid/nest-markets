"""MH-DRIFT-LOCK-REGRESSION-1 — Verify read-only audit endpoints do not
weaken the auto-trading drift lock.

This test asserts a masked-risk invariant: hitting any of the four
read-only audit surfaces shipped in cycles 23-27 must NOT
* call ``BrokerService.submit_auto_order``
* loosen ``assert_auto_trading_allowed()`` (still raises)
* mutate ``trading_control_service`` gate state

The test uses ``unittest.mock`` to assert the broker auto-submit method
is never invoked across a series of GETs, and re-invokes
``assert_auto_trading_allowed()`` afterwards to confirm it still raises.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.broker_service import BrokerService
from app.services.trading_control_service import (
    AutoTradingBlockedError,
    assert_auto_trading_allowed,
    assert_order_submission_allowed,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


READ_ONLY_AUDIT_ENDPOINTS = [
    "/broker/submit-decisions/recent?limit=1",
    "/news-in-decision-log/recent?limit=1",
    "/risk-decisions/recent?limit=1",
    "/llm-logs/recent?limit=1",
]


def test_audit_endpoints_do_not_call_broker_submit_auto_order(client):
    """No audit GET should ever invoke BrokerService.submit_auto_order."""
    with patch.object(
        BrokerService, "submit_auto_order", autospec=True
    ) as mock_auto:
        for path in READ_ONLY_AUDIT_ENDPOINTS:
            resp = client.get(path)
            assert resp.status_code == 200, (
                f"audit endpoint {path} returned {resp.status_code}: "
                f"{resp.text[:200]}"
            )
        assert mock_auto.call_count == 0, (
            "BrokerService.submit_auto_order was invoked while serving "
            "supposedly read-only audit endpoints — drift-lock regression."
        )


def test_assert_auto_trading_allowed_still_raises_after_audit_calls(client):
    """assert_auto_trading_allowed() must remain unconditionally blocking."""
    # Pre-condition: it raises now.
    with pytest.raises(AutoTradingBlockedError):
        assert_auto_trading_allowed()

    for path in READ_ONLY_AUDIT_ENDPOINTS:
        resp = client.get(path)
        assert resp.status_code == 200

    # Post-condition: still raises after touching every audit surface.
    with pytest.raises(AutoTradingBlockedError):
        assert_auto_trading_allowed()


def test_assert_order_submission_allowed_with_auto_intent_still_raises(client):
    """assert_order_submission_allowed(intent='auto') must keep raising."""
    with pytest.raises(AutoTradingBlockedError):
        assert_order_submission_allowed(intent="auto")

    # Touch the audit surface and re-assert.
    for path in READ_ONLY_AUDIT_ENDPOINTS:
        client.get(path)

    with pytest.raises(AutoTradingBlockedError):
        assert_order_submission_allowed(intent="auto")
