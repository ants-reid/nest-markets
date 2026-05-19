"""Drift-lock pin: the ``response_model=`` annotations on safety-critical
HTTP routes must not silently change.

Cycle 63 — MH-DRIFTLOCK-RESPONSE-MODEL-CATALOG.

Why this pin exists
-------------------
Cycle 58 pinned router prefixes/tags; cycle 61 SHA-256-pinned the
Pydantic schema fields themselves; cycle 62 pinned auth-required
routes.  This pin closes the third side of the triangle by recording
which response_model class is bound to each safety-critical route.
A silent swap (e.g. returning a looser schema that omits the trading
mode flag) would be invisible to any of the existing pins.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import re
from pathlib import Path

ROUTE_FILES_ROOT = Path(__file__).resolve().parent.parent / "app" / "api" / "routes"

# Hard safety subset — the routes whose response shape MUST remain
# locked to a specific schema class.
SAFETY_RESPONSE_MODELS: dict[tuple[str, str, str], str] = {
    # (file, method, path) -> response_model class name
    ("execution.py", "post", "/paper"): "PaperExecutionResponse",
    ("workflow.py", "post", "/run"): "WorkflowRunResponse",
    ("execution.py", "post", "/live"): "LiveExecutionResponse",
}

# Broader catalog — every (method, path) -> response_model in the two
# safety-adjacent route files. Any addition/removal here is a real
# surface change that warrants a ledger entry.
EXPECTED_RESPONSE_MODELS: dict[tuple[str, str, str], str] = {
    ("execution.py", "post", "/paper"): "PaperExecutionResponse",
    ("execution.py", "get", "/positions"): "list[PositionResponse]",
    ("execution.py", "get", "/positions/{position_id}/pnl"): "list[PositionPnlSnapshotResponse]",
    ("execution.py", "post", "/positions/{position_id}/snapshot"): "PositionPnlSnapshotResponse",
    ("execution.py", "get", "/paper"): "list[PaperExecutionResponse]",
    ("execution.py", "get", "/paper/{execution_id}"): "PaperExecutionResponse",
    ("execution.py", "get", "/paper/{execution_id}/history"): "dict[str, object]",
    ("execution.py", "post", "/paper/{execution_id}/fill"): "PaperExecutionResponse",
    ("execution.py", "post", "/paper/{execution_id}/close"): "PaperExecutionResponse",
    ("execution.py", "get", "/paper/{execution_id}/journal"): "PaperExecutionJournalResponse",
    ("execution.py", "put", "/paper/{execution_id}/journal"): "PaperExecutionJournalResponse",
    ("execution.py", "post", "/live"): "LiveExecutionResponse",
    ("workflow.py", "post", "/run"): "WorkflowRunResponse",
}

# Find @router.<method>("<path>" ... response_model=<expr> ...) with
# bracket-balanced parsing so subscripts like dict[str, object] survive.
_DECORATOR_HEAD_RE = re.compile(
    r"@router\.(get|post|put|patch|delete)\(\s*"
    r"['\"]([^'\"]+)['\"]"
)


def _extract_response_model_expr(text: str, kw_start: int) -> str | None:
    """Given an offset where 'response_model' begins, walk forward and
    return the response_model expression with brackets balanced."""
    eq = text.find("=", kw_start)
    if eq == -1:
        return None
    i = eq + 1
    while i < len(text) and text[i] in " \t\n":
        i += 1
    start = i
    depth_paren = 1  # we're already inside @router.x(
    depth_brackets = 0
    while i < len(text):
        ch = text[i]
        if ch == "[":
            depth_brackets += 1
        elif ch == "]":
            depth_brackets -= 1
        elif ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren -= 1
            if depth_paren == 0:
                return text[start:i].strip()
        elif ch == "," and depth_brackets == 0 and depth_paren == 1:
            return text[start:i].strip()
        i += 1
    return None


def _scan_file(path: Path) -> dict[tuple[str, str, str], str]:
    text = path.read_text(encoding="utf-8")
    found: dict[tuple[str, str, str], str] = {}
    for head in _DECORATOR_HEAD_RE.finditer(text):
        method = head.group(1).lower()
        url = head.group(2)
        # Search for 'response_model' inside this decorator call only:
        # find next ')' at depth 0 from head.end() to scope the search.
        kw_idx = text.find("response_model", head.end())
        if kw_idx == -1:
            continue
        # Make sure the 'response_model' keyword is still inside this call;
        # check no ')' at depth 0 occurs between head.end() and kw_idx.
        depth = 1
        ok = True
        for j in range(head.end(), kw_idx):
            c = text[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    ok = False
                    break
        if not ok:
            continue
        expr = _extract_response_model_expr(text, kw_idx)
        if expr:
            found[(path.name, method, url)] = expr
    return found


def _scan_safety_files() -> dict[tuple[str, str, str], str]:
    out: dict[tuple[str, str, str], str] = {}
    for fname in {"execution.py", "workflow.py"}:
        out.update(_scan_file(ROUTE_FILES_ROOT / fname))
    return out


def test_safety_response_models_unchanged() -> None:
    found = _scan_safety_files()
    drift: list[str] = []
    for key, expected_rm in SAFETY_RESPONSE_MODELS.items():
        if key not in found:
            drift.append(f"  MISSING route {key} expected response_model={expected_rm}")
            continue
        if found[key] != expected_rm:
            drift.append(
                f"  {key}: expected response_model={expected_rm!r}, "
                f"actual={found[key]!r}"
            )
    assert not drift, (
        "Safety route response_model drift detected. These routes are "
        "the auto/live trading surface; their response schema must not "
        "be swapped without explicit drift-lock review.\n"
        + "\n".join(drift)
    )


def test_full_response_model_catalog_exact_match() -> None:
    found = _scan_safety_files()
    expected_keys = set(EXPECTED_RESPONSE_MODELS)
    found_keys = set(found)
    missing = expected_keys - found_keys
    extra = found_keys - expected_keys
    mismatched = [
        f"  {k}: expected={EXPECTED_RESPONSE_MODELS[k]!r} actual={found[k]!r}"
        for k in expected_keys & found_keys
        if found[k] != EXPECTED_RESPONSE_MODELS[k]
    ]
    msg_parts: list[str] = []
    if missing:
        msg_parts.append("Missing routes: " + ", ".join(map(str, sorted(missing))))
    if extra:
        msg_parts.append("Unexpected new routes: " + ", ".join(map(str, sorted(extra))))
    if mismatched:
        msg_parts.append("Mismatched response_model:\n" + "\n".join(mismatched))
    assert not msg_parts, (
        "execution.py / workflow.py response_model catalog drift:\n"
        + "\n".join(msg_parts)
        + "\nIf intentional, update EXPECTED_RESPONSE_MODELS and ledger."
    )


def test_safety_subset_is_subset_of_full_catalog() -> None:
    safety_keys = set(SAFETY_RESPONSE_MODELS)
    full_keys = set(EXPECTED_RESPONSE_MODELS)
    assert safety_keys <= full_keys, (
        f"SAFETY_RESPONSE_MODELS contains keys not in "
        f"EXPECTED_RESPONSE_MODELS: {safety_keys - full_keys}"
    )
    for k, v in SAFETY_RESPONSE_MODELS.items():
        assert EXPECTED_RESPONSE_MODELS[k] == v, (
            f"Safety subset response_model {v!r} for {k} disagrees with "
            f"full catalog {EXPECTED_RESPONSE_MODELS[k]!r}"
        )
