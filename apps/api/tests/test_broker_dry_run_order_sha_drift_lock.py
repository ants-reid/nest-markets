"""MH-DRIFTLOCK-BROKER-DRY-RUN-ORDER-SHA-PIN

Byte-exact SHA-256 pin on ``BrokerService.dry_run_order``. The dry-run
path is a safety-affordance used by paper / preview flows; silent edits
could turn a no-op preview into a side-effecting submission.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.broker_service import BrokerService

_EXPECTED_SHA = "1f1215e43e82b36bab21469c65bc1f621301732c2d43fc5abf621573c61f5b6c"
_EXPECTED_LEN = 3190


def test_broker_dry_run_order_sha_pin() -> None:
    src = inspect.getsource(BrokerService.dry_run_order)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"BrokerService.dry_run_order SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert len(src) == _EXPECTED_LEN, (
        f"BrokerService.dry_run_order length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )


def test_broker_dry_run_order_keeps_dry_run_token() -> None:
    src = inspect.getsource(BrokerService.dry_run_order)
    assert "dry_run" in src, (
        "BrokerService.dry_run_order must still reference dry_run semantics."
    )
