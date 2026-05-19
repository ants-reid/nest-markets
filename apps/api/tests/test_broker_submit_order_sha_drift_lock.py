"""MH-DRIFTLOCK-BROKER-SUBMIT-ORDER-SHA-PIN

Byte-exact SHA-256 pin on ``BrokerService.submit_order``.
This is the manual-intent delegator that calls the internal
``_submit_order_for_intent(request, intent="manual")``. Silently
flipping the intent string or bypassing the delegator would change
which audit-attribution path the order takes.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.broker_service import BrokerService

_EXPECTED_SHA = "02c7d180734f98bb5ab4145ae85b9f2d5b471fd5ad186d4c021b47e2cfe3270a"
_EXPECTED_LEN = 149


def test_broker_submit_order_sha_pin() -> None:
    src = inspect.getsource(BrokerService.submit_order)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"BrokerService.submit_order SHA drift: expected {_EXPECTED_SHA}, got {sha}. "
        'The manual-intent delegator must continue to call _submit_order_for_intent(intent="manual").'
    )
    assert len(src) == _EXPECTED_LEN, (
        f"BrokerService.submit_order length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )


def test_broker_submit_order_uses_manual_intent_token() -> None:
    src = inspect.getsource(BrokerService.submit_order)
    assert 'intent="manual"' in src, (
        "BrokerService.submit_order must continue to forward intent=\"manual\" so that "
        "audit attribution does not silently shift to auto/system."
    )
