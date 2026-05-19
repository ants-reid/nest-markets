"""Drift-lock: PaperExecutionService.submit_order source pin (cycle 69).

Pins the byte-exact source of ``PaperExecutionService.submit_order`` —
the deterministic paper-fill path used by ``/execution/paper`` and
the workflow runner. Silent edits here would change paper P&L without
going through any tracked phase.

Test-only / additive.
"""

from __future__ import annotations

import hashlib
import inspect

from app.services.paper_execution_service import PaperExecutionService

EXPECTED_SUBMIT_ORDER_SHA = (
    "5c183f9728b3bfd9b1a2bb5eb9d723c99040abdea141e6e847860a92d90a8ea1"
)
EXPECTED_SUBMIT_ORDER_LEN = 948


def test_paper_execution_submit_order_source_pinned() -> None:
    src = inspect.getsource(PaperExecutionService.submit_order).encode("utf-8")
    actual_sha = hashlib.sha256(src).hexdigest()
    actual_len = len(src)
    assert actual_sha == EXPECTED_SUBMIT_ORDER_SHA and actual_len == EXPECTED_SUBMIT_ORDER_LEN, (
        "PaperExecutionService.submit_order source drift detected.\n"
        f"  expected sha={EXPECTED_SUBMIT_ORDER_SHA} len={EXPECTED_SUBMIT_ORDER_LEN}\n"
        f"  actual   sha={actual_sha} len={actual_len}\n"
        "Edits to this method change paper P&L semantics. If "
        "intentional, update EXPECTED_SUBMIT_ORDER_SHA and append a "
        "ledger entry confirming paper-fill behaviour was reviewed."
    )


def test_paper_execution_service_has_submit_order() -> None:
    assert callable(getattr(PaperExecutionService, "submit_order", None)), (
        "PaperExecutionService.submit_order disappeared from the class."
    )
