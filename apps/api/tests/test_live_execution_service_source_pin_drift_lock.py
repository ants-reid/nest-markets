"""Drift-lock: SHA-256 source pin of LiveExecutionService methods (cycle 66).

Pins the byte-exact source of the three execution-control methods on
``LiveExecutionService``:

* ``submit``        — primary route used by /execution/live and the
  workflow runner. Contains the Gate-4 ``auto_live`` short-circuit.
* ``submit_order``  — legacy path that MUST always raise
  ``LiveExecutionDisabledError``.
* ``cancel_order``  — also MUST always raise.

A silent edit to any of these would change live-trading semantics
without going through ``trading_control_service.py``.

Behavioural floors:
* ``LiveExecutionService().submit(execution_mode='auto_live', ...)``
  returns ``accepted=False, status='disabled'`` and the pre-MVP reason
  string.
* ``LiveExecutionService().submit_order(...)`` raises
  ``LiveExecutionDisabledError``.
* ``LiveExecutionService().cancel_order(...)`` raises
  ``LiveExecutionDisabledError``.

Test-only / additive.
"""

from __future__ import annotations

import hashlib
import inspect
from uuid import uuid4

import pytest

from app.services.live_execution_service import (
    LiveExecutionDisabledError,
    LiveExecutionRequest,
    LiveExecutionService,
)

EXPECTED_METHOD_SHAS: dict[str, tuple[str, int]] = {
    "submit": (
        "522b38f0e79282ab0620b20c9e25c112ae1b8c2ce120c84f002d50d475a02824",
        2700,
    ),
    "submit_order": (
        "8eec5ce8da82beafbfc9f94fb24cef4ce6f541e617e55991b03aeeded9f6fe99",
        658,
    ),
    "cancel_order": (
        "58704c1591618167a247f1e5d1fc877af005a84c9f261ceda1fc996dee3cb0bd",
        188,
    ),
}


def _sha_and_len(method_name: str) -> tuple[str, int]:
    fn = getattr(LiveExecutionService, method_name)
    src = inspect.getsource(fn).encode("utf-8")
    return hashlib.sha256(src).hexdigest(), len(src)


def test_live_execution_service_method_sources_pinned() -> None:
    drift: list[str] = []
    for name, (expected_sha, expected_len) in EXPECTED_METHOD_SHAS.items():
        actual_sha, actual_len = _sha_and_len(name)
        if actual_sha != expected_sha or actual_len != expected_len:
            drift.append(
                f"  LiveExecutionService.{name}: "
                f"expected sha={expected_sha} len={expected_len}, "
                f"actual sha={actual_sha} len={actual_len}"
            )
    assert not drift, (
        "LiveExecutionService method source drift detected. ANY edit "
        "to these methods can change live-trading semantics outside "
        "the trading_control_service.py guard surface.\n"
        + "\n".join(drift)
        + "\nIf the change is intentional and reviewed, update "
        "EXPECTED_METHOD_SHAS with the new digest and explicitly note "
        "in the build ledger that Gate-4 invariants still hold."
    )


def test_submit_auto_live_returns_disabled_sentinel() -> None:
    svc = LiveExecutionService()
    req = LiveExecutionRequest(
        asset="AAPL",
        side="buy",
        qty=1.0,
        notional=100.0,
        stop_price=95.0,
        target_price=110.0,
        execution_mode="auto_live",
    )
    result = svc.submit(req)
    assert result.accepted is False
    assert result.status == "disabled"
    assert result.reason == "live_execution_disabled_in_mvp"


def test_submit_order_always_raises_disabled() -> None:
    svc = LiveExecutionService()
    with pytest.raises(LiveExecutionDisabledError):
        svc.submit_order(
            risk_decision_id=uuid4(),
            asset_id=uuid4(),
            direction="long",
            quantity=1.0,
        )


def test_cancel_order_always_raises_disabled() -> None:
    svc = LiveExecutionService()
    with pytest.raises(LiveExecutionDisabledError):
        svc.cancel_order(broker_order_id="x")
