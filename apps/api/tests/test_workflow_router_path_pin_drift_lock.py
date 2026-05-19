"""MH-DRIFTLOCK-WORKFLOW-ROUTER-PATH-PIN

Pins the workflow router exposes ``POST /workflow/run``. The workflow router
is the orchestrator entrypoint that triggers signal->risk->approval flow.
"""
from __future__ import annotations

from app.api.routes.workflow import router as workflow_router

_EXPECTED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {("POST", "/workflow/run")}
)


def _router_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for r in workflow_router.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None) or set()
        if path is None:
            continue
        for m in methods:
            if m in {"HEAD", "OPTIONS"}:
                continue
            pairs.add((m, path))
    return pairs


def test_workflow_router_run_endpoint_present() -> None:
    actual = _router_pairs()
    missing = _EXPECTED_ROUTES - actual
    assert not missing, f"Workflow router missing safety endpoints: {sorted(missing)}"


def test_workflow_router_path_count_floor() -> None:
    n = len(_router_pairs())
    assert n >= 1, f"Workflow router exposes no method/path pairs: {n}"
