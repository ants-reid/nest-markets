"""MH-DRIFTLOCK-PAPER-EXECUTION-SUBMIT-ORDER-SHA-PIN

SHA-256 source pins on the two paper-execution submit_order entrypoints:
``StatelessPaperExecutionService.submit_order`` and
``PaperExecutionService.submit_order``. Paper submit is the closest analogue
to live submission — silent edits must be loud.
"""
from __future__ import annotations

import hashlib
import inspect

from app.services.paper_execution_service import (
    PaperExecutionService,
    StatelessPaperExecutionService,
)

_EXPECTED_STATELESS_SHA = "1ad7a289aab50e9af05936e564afa916d17fab1bb69b3f5263f513deaff670fb"
_EXPECTED_STATELESS_LEN = 962
_EXPECTED_STATEFUL_SHA = "5c183f9728b3bfd9b1a2bb5eb9d723c99040abdea141e6e847860a92d90a8ea1"
_EXPECTED_STATEFUL_LEN = 948


def _meta(fn) -> tuple[str, int]:
    src = inspect.getsource(fn)
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src)


def test_stateless_paper_execution_submit_order_sha_pin() -> None:
    sha, length = _meta(StatelessPaperExecutionService.submit_order)
    assert sha == _EXPECTED_STATELESS_SHA, (
        f"StatelessPaperExecutionService.submit_order SHA drift: "
        f"expected {_EXPECTED_STATELESS_SHA}, got {sha}."
    )
    assert length == _EXPECTED_STATELESS_LEN, (
        f"StatelessPaperExecutionService.submit_order length drift: "
        f"expected {_EXPECTED_STATELESS_LEN}, got {length}"
    )


def test_stateful_paper_execution_submit_order_sha_pin() -> None:
    sha, length = _meta(PaperExecutionService.submit_order)
    assert sha == _EXPECTED_STATEFUL_SHA, (
        f"PaperExecutionService.submit_order SHA drift: "
        f"expected {_EXPECTED_STATEFUL_SHA}, got {sha}."
    )
    assert length == _EXPECTED_STATEFUL_LEN, (
        f"PaperExecutionService.submit_order length drift: "
        f"expected {_EXPECTED_STATEFUL_LEN}, got {length}"
    )
