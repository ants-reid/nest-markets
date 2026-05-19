"""Drift-lock pin: ``Depends(...)`` provider catalog on the safety routes.

Cycle 65 — MH-DRIFTLOCK-DEPENDENCY-INJECTION-CATALOG.

Why this pin exists
-------------------
Cycle 62 pins WHICH route files carry ``Depends(api_key_auth)``; cycle
63 SHA-256-pins the auth middleware itself; cycle 64 pins idempotency
middleware bytes. This pin closes the wiring side: which dependency
PROVIDERS are bound to each safety route. A silent swap (e.g.
replacing ``check_idempotency_key`` with a no-op fixture, or rebinding
``get_db_session`` to an in-memory mock) would break the safety story
without flipping any prior pin.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import re
from pathlib import Path

ROUTE_FILES_ROOT = Path(__file__).resolve().parent.parent / "app" / "api" / "routes"

# Hard safety subset: per route, the EXACT set of provider names that
# must appear in Depends(...) annotations on the function signature.
SAFETY_DEPENDENCY_CATALOG: dict[tuple[str, str, str], set[str]] = {
    ("execution.py", "post", "/paper"): {
        "api_key_auth",
        "check_idempotency_key",
    },
    ("workflow.py", "post", "/run"): {
        "api_key_auth",
        "check_idempotency_key",
        "get_db_session",
    },
}

_DECORATOR_HEAD_RE = re.compile(
    r"@router\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]"
)


def _find_function_block(text: str, decorator_end: int) -> str:
    """From the end of a decorator, capture text up to the next blank
    line at column 0 — enough to cover the function signature."""
    # Find next ``def`` after the decorator.
    def_idx = text.find("def ", decorator_end)
    if def_idx == -1:
        return ""
    # Find the closing paren of the def signature with bracket balance.
    open_paren = text.find("(", def_idx)
    if open_paren == -1:
        return ""
    depth = 0
    i = open_paren
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[def_idx : i + 1]
        i += 1
    return ""


_DEPENDS_PROVIDER_RE = re.compile(r"Depends\(\s*([A-Za-z_][\w.]*)\s*\)")


def _extract_providers(route_file: Path, target_method: str, target_path: str) -> set[str]:
    text = route_file.read_text(encoding="utf-8")
    providers: set[str] = set()
    for head in _DECORATOR_HEAD_RE.finditer(text):
        if head.group(1).lower() != target_method:
            continue
        if head.group(2) != target_path:
            continue
        # Find the close-paren of this decorator (depth-aware).
        depth = 1
        i = head.end()
        while i < len(text) and depth:
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            i += 1
        block = _find_function_block(text, i)
        for m in _DEPENDS_PROVIDER_RE.finditer(block):
            providers.add(m.group(1).split(".")[-1])
        return providers
    return providers


def test_safety_route_dependency_providers_unchanged() -> None:
    drift: list[str] = []
    for (fname, method, path), expected in SAFETY_DEPENDENCY_CATALOG.items():
        route_file = ROUTE_FILES_ROOT / fname
        actual = _extract_providers(route_file, method, path)
        missing = expected - actual
        if missing:
            drift.append(
                f"  {fname} {method.upper()} {path}: missing Depends(...) providers: {sorted(missing)}"
            )
    assert not drift, (
        "Safety-route Depends(...) provider drift detected. The trading "
        "surface relies on EVERY listed provider being wired. A removal "
        "would silently bypass auth / idempotency / session scoping.\n"
        + "\n".join(drift)
    )


def test_safety_routes_use_api_key_auth_provider() -> None:
    """Standalone hard guard: api_key_auth MUST appear in both routes."""
    for (fname, method, path) in SAFETY_DEPENDENCY_CATALOG:
        providers = _extract_providers(ROUTE_FILES_ROOT / fname, method, path)
        assert "api_key_auth" in providers, (
            f"{fname} {method.upper()} {path} no longer wires "
            "Depends(api_key_auth). Auth has been removed from a safety "
            "route."
        )


def test_safety_routes_use_check_idempotency_key_provider() -> None:
    """Standalone hard guard: check_idempotency_key MUST appear."""
    for (fname, method, path) in SAFETY_DEPENDENCY_CATALOG:
        providers = _extract_providers(ROUTE_FILES_ROOT / fname, method, path)
        assert "check_idempotency_key" in providers, (
            f"{fname} {method.upper()} {path} no longer wires "
            "Depends(check_idempotency_key). Double-submission protection "
            "has been removed from a safety route."
        )
