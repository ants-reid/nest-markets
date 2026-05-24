"""MH-DRIFTLOCK-BROKER-SERVICE-SUBMIT-AUTO-ORDER-SHA-PIN

SHA-256 source pin on ``BrokerService.submit_auto_order``. This is the
auto-trading entrypoint guarded by ``assert_auto_trading_allowed``; any
silent edit must be loud.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.broker_service import BrokerService

_EXPECTED_SHA = "73bdc642b5b738614d4ab9523b6837964d6ce33198fb4b0af554378d5294b48a"
_EXPECTED_LEN = 554


def _src_meta() -> tuple[str, int, str]:
    src = inspect.getsource(BrokerService.submit_auto_order)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src), src


def test_submit_auto_order_sha_pin() -> None:
    sha, length, _ = _src_meta()
    assert sha == _EXPECTED_SHA, (
        f"BrokerService.submit_auto_order SHA drift: expected {_EXPECTED_SHA}, got {sha}. "
        "Auto-trading entrypoint changed — review carefully before updating the pin."
    )
    assert length == _EXPECTED_LEN, (
        f"BrokerService.submit_auto_order length drift: expected {_EXPECTED_LEN}, got {length}"
    )


def test_submit_auto_order_routes_through_intent_auto() -> None:
    _, _, src = _src_meta()
    assert "_submit_order_for_intent" in src, (
        "BrokerService.submit_auto_order must delegate to _submit_order_for_intent."
    )
    assert 'intent="auto"' in src, (
        "BrokerService.submit_auto_order must declare intent=\"auto\" so the gate path is taken."
    )
