"""MH-DRIFTLOCK-WORKFLOW-RUN-HANDLER-SHA-PIN

SHA-256 source pin on the FastAPI handler bound to ``POST /workflow/run``.
The workflow run handler is the orchestrator entry point that drives
signal → risk → approval → execution; silent edits must be loud.
"""
from __future__ import annotations

import hashlib
import inspect

from app.api.routes.workflow import router as workflow_router

_EXPECTED_SHA = "2df2fb7d7b771a5dec36abf1e45076e81a85a271a3a1d01f7b68b6da5e349eb2"
_EXPECTED_LEN = 2880
_EXPECTED_NAME = "run_workflow"


def _resolve_endpoint():
    for r in workflow_router.routes:
        if getattr(r, "path", "") == "/workflow/run" and "POST" in (getattr(r, "methods", None) or set()):
            return r.endpoint
    raise AssertionError("workflow router lost POST /workflow/run route")


def test_workflow_run_endpoint_name_pin() -> None:
    ep = _resolve_endpoint()
    assert ep.__name__ == _EXPECTED_NAME, (
        f"workflow run handler renamed: expected {_EXPECTED_NAME!r}, got {ep.__name__!r}"
    )


def test_workflow_run_endpoint_sha_pin() -> None:
    ep = _resolve_endpoint()
    src = inspect.getsource(ep)
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    assert sha == _EXPECTED_SHA, (
        f"workflow run handler SHA drift: expected {_EXPECTED_SHA}, got {sha}."
    )
    assert len(src) == _EXPECTED_LEN, (
        f"workflow run handler length drift: expected {_EXPECTED_LEN}, got {len(src)}"
    )
