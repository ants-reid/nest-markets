"""MH-DRIFTLOCK-EXECUTION-ROUTER-PATH-CATALOG

Pins the exact set of paths exposed by the execution router. The execution
router carries the Gate 4 ``/execution/live`` endpoint and the paper-trading
surface — silent removal or rename would shift the surface the safety tests
guard.
"""
from __future__ import annotations

from app.api.routes.execution import router as execution_router

# Each tuple = (method, path) on the router (path is router-relative).
_EXPECTED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/execution/paper"),
        ("GET", "/execution/positions"),
        ("GET", "/execution/positions/{position_id}/pnl"),
        ("POST", "/execution/positions/{position_id}/snapshot"),
        ("GET", "/execution/paper"),
        ("GET", "/execution/paper/{execution_id}"),
        ("GET", "/execution/paper/{execution_id}/history"),
        ("POST", "/execution/paper/{execution_id}/fill"),
        ("POST", "/execution/paper/{execution_id}/close"),
        ("GET", "/execution/paper/{execution_id}/journal"),
        ("PUT", "/execution/paper/{execution_id}/journal"),
        ("POST", "/execution/live"),
    }
)


def _router_method_path_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for r in execution_router.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None) or set()
        if path is None:
            continue
        for m in methods:
            if m in {"HEAD", "OPTIONS"}:
                continue
            pairs.add((m, path))
    return pairs


def test_execution_router_required_paths_present() -> None:
    actual = _router_method_path_pairs()
    missing = _EXPECTED_ROUTES - actual
    assert not missing, f"Execution router missing safety paths: {sorted(missing)}"


def test_execution_router_live_post_present() -> None:
    # Gate 4 entrypoint MUST remain mounted (returns disabled sentinel).
    assert ("POST", "/execution/live") in _router_method_path_pairs()


def test_execution_router_path_count_floor() -> None:
    n = len(_router_method_path_pairs())
    assert n >= len(_EXPECTED_ROUTES), (
        f"Execution router method/path pair count {n} below floor {len(_EXPECTED_ROUTES)}"
    )
